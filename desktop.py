"""Native Python desktop edition. Run: python desktop.py"""
from __future__ import annotations

import base64
import io
import math
import os
import random
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import Canvas, filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from server.audio import DesktopAudio
from server.documents import MAX_BYTES, import_document
from server.study import LibraryStore, StudySession

BG = ('#F4F7FC', '#11151E')
SURFACE = ('#FFFFFF', '#1B2230')
INK = ('#202B40', '#EDF2FC')
MUTED = ('#647189', '#A3B0C6')
BORDER = ('#E1E7F1', '#303C50')
SOFT = ('#EBF0F8', '#252F40')
BLUE, RED, GREEN, YELLOW = '#1967D2', '#D93025', '#188038', '#FBBC05'
FONT_FAMILY = 'Segoe UI' if os.name == 'nt' else 'Arial'


def font(size=18, bold=False):
    candidates = [Path(os.getenv('WINDIR', 'C:/Windows')) / 'Fonts' / ('segoeuib.ttf' if bold else 'segoeui.ttf'),
                  Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
                  Path('/System/Library/Fonts/Supplemental/Arial.ttf')]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


class NoteThat:
    def __init__(self, root, data_directory=None):
        self.root = root
        self.store = LibraryStore(data_directory)
        self.preferences = self.store.preferences
        ctk.set_appearance_mode('dark' if self.preferences['dark'] else 'light')
        self.audio = DesktopAudio()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._closed = False
        self._animating = False
        self._importing = False
        self._drag_start = None
        self._drag_offset = 0
        self._photo = None
        self._base = None
        self._scheduled = set()
        self._confetti_after = None
        self.dialog = None
        self.confetti_kind = None
        self.session = StudySession(next((d for d in self.store.decks if d['id'] == self.store.selected), self.store.decks[0]))
        root.title('note that — a little more familiar')
        root.geometry('1180x850')
        root.minsize(980, 740)
        root.configure(fg_color=BG)
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.build()
        root.bind('<Left>', lambda _: self.decide('confident'))
        root.bind('<Right>', lambda _: self.decide('revisit'))
        root.bind('<Key-z>', lambda _: self.undo())
        root.bind('<Key-Z>', lambda _: self.undo())
        self.status.configure(text=self.store.warning or 'A little less cramming. A little more understanding.')
        self.later(60, self.refresh)

    def later(self, milliseconds, callback):
        if self._closed:
            return None
        holder = []
        def run():
            self._scheduled.discard(holder[0])
            if not self._closed:
                callback()
        identifier = self.root.after(milliseconds, run)
        holder.append(identifier)
        self._scheduled.add(identifier)
        return identifier

    def text(self, parent, text, size=12, bold=False, color=INK, **kwargs):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(family=FONT_FAMILY, size=size, weight='bold' if bold else 'normal'), text_color=color, **kwargs)

    def button(self, parent, text, command, color=SOFT, text_color=INK, **kwargs):
        kwargs.setdefault('height', 40)
        return ctk.CTkButton(parent, text=text, command=command, fg_color=color, text_color=text_color, hover_color=('#DFE8F6', '#34425A') if isinstance(color, tuple) else color, font=ctk.CTkFont(family=FONT_FAMILY, size=12, weight='bold'), corner_radius=13, **kwargs)

    def build(self):
        side = ctk.CTkFrame(self.root, width=200, corner_radius=0, fg_color=SURFACE)
        side.grid(row=0, column=0, sticky='nsew')
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(7, weight=1)
        brand = ctk.CTkFrame(side, fg_color='transparent')
        brand.grid(row=0, column=0, padx=20, pady=(25, 8), sticky='ew')
        self.bolt(brand).pack(side='left')
        self.text(brand, 'note that', 24, True).pack(side='left', padx=7)
        self.text(side, 'A LITTLE MORE FAMILIAR.', 9, color=MUTED).grid(row=1, column=0, padx=20, pady=(2, 22), sticky='w')
        self.import_button = self.button(side, '+  Add files', self.choose_file, RED, 'white')
        self.import_button.grid(row=2, column=0, padx=20, pady=6, sticky='ew')
        self.study_button = self.button(side, '▤  Study space', lambda: self.show('study'), ('#E8F0FE', '#1E2D43'), ('#1967D2', '#8AB4F8'))
        self.study_button.grid(row=3, column=0, padx=20, pady=5, sticky='ew')
        self.button(side, '▣  My library', lambda: self.show('library')).grid(row=4, column=0, padx=20, pady=5, sticky='ew')
        self.button(side, '✧  Your progress', lambda: self.show('progress')).grid(row=5, column=0, padx=20, pady=5, sticky='ew')
        steps = ctk.CTkFrame(side, fg_color=BG, corner_radius=19)
        steps.grid(row=6, column=0, padx=20, pady=25, sticky='ew')
        self.text(steps, 'THREE LITTLE STEPS', 8, color=MUTED).pack(anchor='w', padx=15, pady=(17, 9))
        for n, label, color in [(1, 'Bring your slides', BLUE), (2, 'Swipe and learn', RED), (3, 'Come back stronger', GREEN)]:
            row = ctk.CTkFrame(steps, fg_color='transparent')
            row.pack(fill='x', padx=13, pady=(4, 12))
            self.text(row, str(n), 10, True, 'white', fg_color=color, corner_radius=13, width=25, height=25).pack(side='left')
            self.text(row, label, 9).pack(side='left', padx=8)
        privacy = ctk.CTkFrame(side, fg_color='transparent')
        privacy.grid(row=8, column=0, padx=23, pady=(8, 20), sticky='ew')
        self.text(privacy, '✓  Private by default.', 11, True, GREEN).pack(anchor='w')
        self.text(privacy, 'No uploads. No accounts.\nJust you and your next little win.', 10, color=MUTED, justify='left').pack(anchor='w', pady=(10, 0))
        options = ctk.CTkFrame(side, fg_color='transparent')
        options.grid(row=9, column=0, padx=20, pady=(0, 23), sticky='ew')
        self.theme_button = self.button(options, '☼', self.toggle_theme, width=36)
        self.theme_button.pack(side='left')
        self.sound_button = self.button(options, 'Sound off', self.sound_settings, width=112)
        self.sound_button.pack(side='right')
        self.main = ctk.CTkFrame(self.root, fg_color='transparent')
        self.main.grid(row=0, column=1, padx=25, pady=23, sticky='nsew')
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(3, weight=1)
        heading = ctk.CTkFrame(self.main, fg_color='transparent')
        heading.grid(row=0, column=0, sticky='ew')
        self.heading = self.text(heading, 'Your slides, a little clearer.', 27, True)
        self.heading.pack(anchor='w')
        self.text(heading, 'A little focus. One familiar slide at a time.', 11, color=MUTED).pack(anchor='w', pady=(3, 15))
        banner = ctk.CTkFrame(self.main, fg_color=('#E8F0FE', '#1E2D43'), corner_radius=21)
        banner.grid(row=1, column=0, sticky='ew', pady=(0, 19))
        self.bolt(banner).pack(side='right', padx=21)
        self.text(banner, 'Little swipes. Lasting knowledge.\nLeft when you know it. Right for a second look.', 12, True, ('#1967D2', '#8AB4F8'), justify='left').pack(side='left', padx=22, pady=15)
        docbar = ctk.CTkFrame(self.main, fg_color=SURFACE, corner_radius=16, border_width=1, border_color=BORDER)
        docbar.grid(row=2, column=0, sticky='ew', pady=(0, 20))
        self.document_title = self.text(docbar, '', 12, True)
        self.document_title.pack(side='left', padx=16, pady=14)
        self.document_meta = self.text(docbar, '', 10, color=MUTED)
        self.document_meta.pack(side='right', padx=16)
        self.workspace = ctk.CTkFrame(self.main, fg_color='transparent')
        self.workspace.grid(row=3, column=0, sticky='nsew')
        self.workspace.grid_columnconfigure(0, weight=1)
        self.workspace.grid_rowconfigure(0, weight=1)
        self.study_view = ctk.CTkFrame(self.workspace, fg_color='transparent')
        self.study_view.grid(row=0, column=0, sticky='nsew')
        self.study_view.grid_columnconfigure(0, weight=1)
        self.study_view.grid_rowconfigure(1, weight=1)
        self.section_label = self.text(self.study_view, '', 10, True, MUTED, anchor='w')
        self.section_label.grid(row=0, column=0, sticky='ew', pady=(0, 13))
        self.card = ctk.CTkFrame(self.study_view, fg_color=SURFACE, corner_radius=20, border_width=1, border_color=BORDER)
        self.card.grid(row=1, column=0, sticky='nsew')
        self.canvas = Canvas(self.card, width=520, height=320, highlightthickness=0, bd=0, bg=self.color(SURFACE))
        self.canvas.pack(fill='both', expand=True, padx=9, pady=9)
        self.image_item = self.canvas.create_image(0, 0, anchor='center')
        self.canvas.bind('<Configure>', lambda _: self.later(100, self.draw_if_idle))
        self.canvas.bind('<ButtonPress-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag_move)
        self.canvas.bind('<ButtonRelease-1>', self.drag_end)
        controls = ctk.CTkFrame(self.study_view, fg_color='transparent')
        controls.grid(row=2, column=0, pady=(22, 10), sticky='ew')
        controls.grid_columnconfigure((1, 2), weight=1)
        self.undo_button = self.button(controls, 'Undo', self.undo, width=50)
        self.undo_button.grid(row=0, column=0, padx=(0, 9))
        self.know_button = self.button(controls, 'I know this', lambda: self.decide('confident'), GREEN, 'white')
        self.know_button.grid(row=0, column=1, sticky='ew', padx=(0, 6))
        self.later_button = self.button(controls, 'Revisit later  →', lambda: self.decide('revisit'), RED, 'white')
        self.later_button.grid(row=0, column=2, sticky='ew', padx=(6, 0))
        self.continue_button = self.button(self.study_view, 'Continue', self.continue_session, BLUE, 'white')
        self.text(self.study_view, 'Drag the card · Arrow keys to swipe · Z to undo', 9, color=MUTED).grid(row=4, column=0, pady=(2, 14))
        self.review_button = self.button(self.study_view, 'Your revisit pile · 0', self.start_review)
        self.review_button.grid(row=5, column=0, sticky='ew')
        self.path = ctk.CTkFrame(self.workspace, width=207, fg_color='transparent')
        self.path.grid(row=0, column=1, sticky='ns', padx=(22, 0))
        self.path.grid_propagate(False)
        self.text(self.path, 'Your study path', 17, True).pack(anchor='w')
        self.text(self.path, 'Small sections. Steady progress.', 10, color=MUTED).pack(anchor='w', pady=(4, 14))
        self.path_buttons = ctk.CTkScrollableFrame(self.path, fg_color='transparent', height=185, corner_radius=0)
        self.path_buttons.pack(fill='x')
        self.button(self.path, 'Edit sections', self.edit_sections, height=32).pack(fill='x', pady=(6, 14))
        reminder = ctk.CTkFrame(self.path, fg_color=('#FFF7DF', '#332D1E'), corner_radius=17)
        reminder.pack(fill='x', pady=7)
        self.text(reminder, 'A LITTLE REMINDER', 8, color=('#AB7F24', '#D7B96D')).pack(anchor='w', padx=15, pady=(17, 10))
        self.text(reminder, 'You don’t have to know it all.\nYou just have to come back.', 12, color=('#5D4E2B', '#E7D7AB'), justify='left', wraplength=175).pack(anchor='w', padx=15, pady=(0, 17))
        self.stats = self.text(self.path, '', 11, color=MUTED, justify='left')
        self.stats.pack(anchor='w', pady=(21, 12))
        self.progress = ctk.CTkProgressBar(self.path, progress_color=BLUE, fg_color=SOFT, height=5)
        self.progress.pack(fill='x')
        self.other_view = ctk.CTkScrollableFrame(self.workspace, fg_color='transparent', corner_radius=0)
        self.status = self.text(self.main, '', 10, color=MUTED, anchor='w', wraplength=850, justify='left')
        self.status.grid(row=4, column=0, sticky='ew', pady=(18, 0))
        self.update_sound_label()

    def bolt(self, parent):
        image = Image.new('RGBA', (96, 128))
        ImageDraw.Draw(image).polygon([(57, 3), (9, 73), (45, 73), (38, 125), (89, 48), (54, 48)], fill=RED)
        icon = ctk.CTkImage(image, image, size=(24, 32))
        return ctk.CTkLabel(parent, text='', image=icon, width=24, height=32)

    def color(self, pair):
        return pair[1 if self.preferences['dark'] else 0] if isinstance(pair, tuple) else pair

    def save(self):
        try:
            self.store.save()
        except OSError as exc:
            self.status.configure(text=f'Progress could not be saved: {exc}')
            return False
        return True

    def update_sound_label(self):
        self.sound_button.configure(text='Sound on' if self.preferences['sound'] else 'Sound off')
        image = Image.new('RGBA', (72, 72))
        drawing = ImageDraw.Draw(image)
        if self.preferences['dark']:
            drawing.ellipse((10, 10, 62, 62), fill='#F4E8B8', outline='#D9C98C', width=2)
            drawing.ellipse((22, 20, 35, 33), fill='#D9CE9F')
            drawing.ellipse((41, 39, 55, 53), fill='#D9CE9F')
        else:
            drawing.ellipse((24, 24, 48, 48), fill=YELLOW)
            for angle in range(0, 360, 45):
                cosine, sine = math.cos(math.radians(angle)), math.sin(math.radians(angle))
                drawing.line((36 + cosine * 19, 36 + sine * 19, 36 + cosine * 28, 36 + sine * 28), fill=YELLOW, width=5)
        self.theme_button.configure(text='', image=ctk.CTkImage(image, image, size=(18, 18)))

    def toggle_theme(self):
        self.preferences['dark'] = not self.preferences['dark']
        ctk.set_appearance_mode('dark' if self.preferences['dark'] else 'light')
        self.canvas.configure(bg=self.color(SURFACE))
        self.update_sound_label()
        self.save()
        self.draw_if_idle()

    def sound_settings(self):
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.lift()
            return
        dialog = self.dialog = ctk.CTkToplevel(self.root)
        dialog.title('A little atmosphere')
        dialog.geometry('410x380')
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        self.text(dialog, 'A little atmosphere.', 24, True).pack(anchor='w', padx=27, pady=(28, 8))
        self.text(dialog, 'A soft swish. A little chime. Your volume.', 11, color=MUTED).pack(anchor='w', padx=27, pady=(0, 20))
        variable = ctk.BooleanVar(value=self.preferences['sound'])
        def enabled():
            self.preferences['sound'] = variable.get()
            self.update_sound_label()
            if variable.get(): self.play('preview')
            else: self.audio.stop()
            self.save()
        ctk.CTkSwitch(dialog, text='Study sounds', variable=variable, command=enabled, progress_color=BLUE, font=ctk.CTkFont(family=FONT_FAMILY, size=12)).pack(anchor='w', padx=27, pady=10)
        self.text(dialog, 'Volume', 11, color=MUTED).pack(anchor='w', padx=27, pady=(10, 6))
        def volume(value):
            self.preferences['volume'] = value
            self.save()
        slider = ctk.CTkSlider(dialog, from_=0, to=1, command=volume, progress_color=BLUE, button_color=BLUE)
        slider.set(self.preferences['volume'])
        slider.pack(fill='x', padx=27, pady=7)
        motion_var = ctk.BooleanVar(value=self.preferences['reduced_motion'])
        def motion():
            self.preferences['reduced_motion'] = motion_var.get()
            self.save()
        ctk.CTkSwitch(dialog, text='Reduce motion', variable=motion_var, command=motion, progress_color=BLUE, font=ctk.CTkFont(family=FONT_FAMILY, size=12)).pack(anchor='w', padx=27, pady=16)
        self.button(dialog, 'Hear a little preview', lambda: self.play('preview')).pack(fill='x', padx=27, pady=6)

    def play(self, kind):
        if self.preferences['sound']:
            self.audio.play(kind, self.preferences['volume'])
            if self.audio.error:
                self.status.configure(text=self.audio.error)

    def choose_file(self):
        if self._importing:
            return
        filename = filedialog.askopenfilename(parent=self.root, title='Bring your ideas', filetypes=[('Study documents', '*.pdf *.pptx *.png *.jpg *.jpeg *.webp'), ('All files', '*.*')])
        if filename:
            self.import_file(Path(filename))

    def import_file(self, path):
        if self._importing:
            return
        self._importing = True
        self.import_button.configure(state='disabled', text='Preparing…')
        self.status.configure(text=f'Preparing {path.name}. A little moment…')
        def load():
            if path.stat().st_size > MAX_BYTES:
                raise ValueError('Please choose a file under 100 MB.')
            return import_document(path.name, path.read_bytes())
        future = self.executor.submit(load)
        def poll():
            if not future.done():
                self.later(50, poll)
                return
            self._importing = False
            self.import_button.configure(state='normal', text='+  Add files')
            try:
                deck = future.result()
                self.store.decks.append(deck)
                self.select_deck(deck['id'])
                self.status.configure(text='Your document is ready. PPTX uses text cards; export as PDF to preserve slide designs.' if deck['kind'] == 'pptx' else 'Your document is ready. Make yourself at home.')
            except Exception as exc:
                self.status.configure(text=str(exc))
                messagebox.showerror('Could not open this document', str(exc), parent=self.root)
        self.later(50, poll)

    def select_deck(self, identifier):
        if self._animating:
            return
        self.store.selected = identifier
        self.session = StudySession(next(d for d in self.store.decks if d['id'] == identifier))
        self.save()
        self.show('study')
        self.refresh()

    def show(self, view):
        if self._animating:
            return
        self.other_view.grid_remove()
        if view == 'study':
            self.study_view.grid()
            self.path.grid()
            self.heading.configure(text='Your slides, a little clearer.')
            self.refresh()
            return
        self.study_view.grid_remove()
        self.path.grid_remove()
        for child in self.other_view.winfo_children():
            child.destroy()
        self.other_view.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.heading.configure(text='Your little library.' if view == 'library' else 'Look at you grow.')
        if view == 'progress':
            count = sum(len(d['decisions']) for d in self.store.decks)
            known = sum(list(d['decisions'].values()).count('confident') for d in self.store.decks)
            self.text(self.other_view, f'{count} slides explored. {known} feeling confident.', 22, True).pack(anchor='w', padx=8, pady=(10, 20))
        for deck in self.store.decks:
            tile = ctk.CTkFrame(self.other_view, fg_color=SURFACE, corner_radius=18, border_width=1, border_color=BORDER)
            tile.pack(fill='x', padx=2, pady=8)
            explored = len(deck['decisions'])
            self.text(tile, deck['title'], 15, True, anchor='w').pack(fill='x', padx=20, pady=(18, 7))
            self.text(tile, f"{len(deck['slides'])} slides · {len(deck['sections'])} sections · {explored / len(deck['slides']):.0%} explored", 11, color=MUTED).pack(anchor='w', padx=20)
            self.button(tile, 'Pick up where you left off  →', lambda identifier=deck['id']: self.select_deck(identifier), BLUE, 'white').pack(anchor='e', padx=18, pady=17)

    def refresh(self):
        if self._closed:
            return
        deck = self.session.deck
        self.document_title.configure(text=deck['title'][:60])
        self.document_meta.configure(text=f"{len(deck['slides'])} slides · {len(deck['sections'])} sections")
        self.section_label.configure(text='YOUR SECOND LOOK' if self.session.review_ids is not None else f"{self.session.section_index + 1:02}  /  {self.session.section['title'].upper()}")
        known = list(deck['decisions'].values()).count('confident')
        self.review_button.configure(text=f'Your revisit pile · {len(self.session.saved)}   →', state='normal' if self.session.saved else 'disabled')
        self.stats.configure(text=f'{known} confident · {len(self.session.saved)} to revisit\n\n{len(deck["decisions"]) / len(deck["slides"]):.0%} of the way there')
        self.progress.set(len(deck['decisions']) / len(deck['slides']))
        for child in self.path_buttons.winfo_children():
            child.destroy()
        for index, section in enumerate(deck['sections']):
            locked = self.session.first_incomplete is not None and index > self.session.first_incomplete
            done = self.session.done(section)
            active = index == self.session.section_index and self.session.review_ids is None
            label = ('✓' if done else f'{index + 1:02}') + '   ' + section['title'] + f"\n      {section['end'] - section['start'] + 1} slides · " + ('Complete' if done else 'You are here' if active else 'Locked')
            button = self.button(self.path_buttons, label, lambda i=index: self.visit_section(i), ('#E8F0FE', '#1E2D43') if active else SOFT, ('#1967D2', '#8AB4F8') if active else INK, height=61, anchor='w')
            button.configure(state='disabled' if locked else 'normal', font=ctk.CTkFont(family=FONT_FAMILY, size=10))
            button.pack(fill='x', pady=4)
        self.update_controls()
        self.draw_slide()

    def update_controls(self):
        active = self.session.slide is not None and not self._animating
        self.know_button.configure(state='normal' if active else 'disabled')
        self.later_button.configure(state='normal' if active else 'disabled')
        self.undo_button.configure(state='normal' if self.session.history and not self._animating else 'disabled')
        if self.session.slide is None:
            self.continue_button.configure(text='Back to my study path  →' if self.session.review_ids is not None else 'On to the next section  →' if self.session.first_incomplete is not None else 'Finish this session  ✓')
            self.continue_button.grid(row=3, column=0, sticky='ew', pady=(4, 8))
        else:
            self.continue_button.grid_remove()

    def wrapped(self, draw, text, x, y, width, chosen_font, fill, spacing=8):
        for paragraph in text.split('\n'):
            line = ''
            for word in paragraph.split():
                candidate = f'{line} {word}'.strip()
                if line and draw.textlength(candidate, font=chosen_font) > width:
                    draw.text((x, y), line, font=chosen_font, fill=fill)
                    y += chosen_font.size + spacing
                    line = word
                else:
                    line = candidate
            if line:
                draw.text((x, y), line, font=chosen_font, fill=fill)
                y += chosen_font.size + spacing
        return y

    def make_card(self):
        width, height = max(200, self.canvas.winfo_width()), max(200, self.canvas.winfo_height())
        background, ink, muted = self.color(SURFACE), self.color(INK), self.color(MUTED)
        image = Image.new('RGB', (width, height), background)
        slide = self.session.slide
        if slide and slide.get('image'):
            with Image.open(io.BytesIO(base64.b64decode(slide['image'].split(',', 1)[1]))) as page:
                page.thumbnail((width - 12, height - 12))
                image.paste(page.convert('RGB'), ((width - page.width) // 2, (height - page.height) // 2))
            return image
        draw = ImageDraw.Draw(image)
        draw.text((22, 15), 'NOTE THAT · A LITTLE MORE FAMILIAR', font=font(9), fill=muted)
        if slide:
            draw.text((width - 38, 15), str(slide.get('page', '')), font=font(9), fill=muted)
            draw.text((22, max(47, height * .19)), slide.get('kicker', 'TAKE A MOMENT. TAKE IT IN.')[:60], font=font(8, True), fill='#4285F4')
            y = self.wrapped(draw, slide['title'], 22, max(67, height * .27), width - 44, font(29 if len(slide['title']) < 65 else 22, True), ink, 5)
            self.wrapped(draw, slide['body'], 22, y + 16, width - 44, font(14), muted, 7)
        else:
            review_done = self.session.review_ids is not None
            complete = self.session.first_incomplete is None and self.session.checkpoint is None
            heading = 'That’s your second look.' if review_done else 'You made it through.' if complete else 'Section, sorted.'
            draw.ellipse((width // 2 - 25, 45, width // 2 + 25, 95), fill='#E6F4EA')
            draw.text((width // 2 - 10, 52), '✓', font=font(28, True), fill=GREEN)
            self.wrapped(draw, heading, 25, 125, width - 50, font(29, True), ink)
            self.wrapped(draw, 'Every second look is a step toward understanding.' if review_done else 'A little progress. A lot to feel good about.', 25, 190, width - 50, font(14), muted)
        draw.line((22, height - 36, width - 22, height - 36), fill=self.color(BORDER), width=1)
        draw.text((22, height - 26), 'A little more familiar, one slide at a time.', font=font(8), fill=muted)
        return image

    def draw_slide(self):
        if self._closed:
            return
        self._base = self.make_card()
        self.paint(0)

    def draw_if_idle(self):
        if not self._animating:
            self.draw_slide()

    def paint(self, offset=0, scale_x=1, scale_y=1):
        if self._base is None:
            return
        image = self._base
        if abs(scale_x - 1) > .001 or abs(scale_y - 1) > .001:
            image = image.resize((max(1, round(image.width * scale_x)), max(1, round(image.height * scale_y))), Image.Resampling.BILINEAR)
        self._photo = ImageTk.PhotoImage(image, master=self.root)
        self.canvas.itemconfigure(self.image_item, image=self._photo)
        self.canvas.coords(self.image_item, self.canvas.winfo_width() / 2 + offset, self.canvas.winfo_height() / 2)

    def drag_start(self, event):
        if not self._animating and self.session.slide:
            self._drag_start = event.x
            self._drag_offset = 0

    def drag_move(self, event):
        if self._drag_start is not None:
            self._drag_offset = (event.x - self._drag_start) * .85
            if not self.preferences['reduced_motion']:
                stretch = min(abs(self._drag_offset) / 5000, .025)
                self.paint(self._drag_offset, 1 - stretch, 1 + stretch)

    def drag_end(self, event):
        if self._drag_start is None:
            return
        offset = event.x - self._drag_start
        self._drag_start = None
        if abs(offset) >= 85:
            self.decide('revisit' if offset > 0 else 'confident')
        else:
            self._drag_offset = 0
            self.spring_in()

    def decide(self, decision):
        if self._animating or not self.session.slide or (self.dialog and self.dialog.winfo_exists()):
            return
        self._animating = True
        self.update_controls()
        if self.preferences['reduced_motion']:
            self.apply_decision(decision)
            return
        start, offset = time.perf_counter(), self._drag_offset
        direction = 1 if decision == 'revisit' else -1
        def frame():
            elapsed = min(1, (time.perf_counter() - start) / .23)
            ease = elapsed * elapsed * (3 - 2 * elapsed)
            position = offset + (direction * (self.canvas.winfo_width() + 30) - offset) * ease
            self.paint(position, 1 - .025 * math.sin(elapsed * math.pi), 1 + .025 * math.sin(elapsed * math.pi))
            if elapsed < 1:
                self.later(14, frame)
            else:
                self.apply_decision(decision)
        frame()

    def apply_decision(self, decision):
        milestone = self.session.classify(decision)
        self._drag_offset = 0
        saved = self.save()
        self.refresh()
        if saved:
            self.status.configure(text='Your progress is saved. A little more familiar.' if milestone not in {'section', 'document'} else 'Every page explored. Look at you go!' if milestone == 'document' else 'One section closer. Look at you go!')
        self.play(milestone if milestone in {'section', 'document'} else decision)
        if milestone in {'section', 'document'}:
            self.celebrate(milestone)
        self.spring_in()

    def spring_in(self):
        if self.preferences['reduced_motion']:
            self._animating = False
            self.paint(0)
            self.update_controls()
            return
        self._animating = True
        start = time.perf_counter()
        def frame():
            elapsed = time.perf_counter() - start
            wobble = math.exp(-8 * elapsed) * math.cos(17 * elapsed)
            self.paint(0, 1 - .055 * wobble, 1 + .055 * wobble)
            if elapsed < .62:
                self.later(14, frame)
            else:
                self.paint(0)
                self._animating = False
                self.update_controls()
        frame()

    def celebrate(self, kind):
        self.confetti_kind = kind
        if self._confetti_after:
            self.root.after_cancel(self._confetti_after)
        self.canvas.delete('confetti')
        if self.preferences['reduced_motion']:
            return
        width, height = self.canvas.winfo_width(), self.canvas.winfo_height()
        pieces = []
        for _ in range(110 if kind == 'document' else 55):
            size = random.randrange(4, 9)
            x, y = width * random.choice((.25, .75)), height * .65
            item = self.canvas.create_rectangle(x, y, x + size, y + size / 2, fill=random.choice([BLUE, RED, GREEN, YELLOW]), outline='', tags='confetti')
            pieces.append([item, random.uniform(-160, 160), random.uniform(-290, -130)])
        start, previous = time.perf_counter(), [time.perf_counter()]
        def frame():
            now = time.perf_counter()
            dt = min(now - previous[0], .05)
            previous[0] = now
            for piece in pieces:
                piece[2] += 240 * dt
                self.canvas.move(piece[0], piece[1] * dt, piece[2] * dt)
            if now - start < 2.6:
                self._confetti_after = self.later(16, frame)
            else:
                self.canvas.delete('confetti')
                self._confetti_after = None
        frame()

    def undo(self):
        if self._animating:
            return
        if self.session.undo():
            self.canvas.delete('confetti')
            self.confetti_kind = None
            self.save()
            self.refresh()
            self.status.configure(text='Last swipe undone. A fresh look.')

    def continue_session(self):
        if self._animating:
            return
        if self.session.first_incomplete is None and self.session.checkpoint is None and self.session.review_ids is None:
            self.show('library')
            return
        self.session.continue_studying()
        self.refresh()

    def start_review(self):
        if not self._animating and self.session.saved:
            self.session.review()
            self.refresh()

    def visit_section(self, index):
        if self._animating:
            return
        incomplete = self.session.first_incomplete
        if incomplete is not None and index > incomplete:
            return
        section = self.session.deck['sections'][index]
        if self.session.done(section):
            self.session.review([s['id'] for s in self.session.deck['slides'][section['start']:section['end'] + 1]])
        else:
            self.session.review_ids = None
            self.session.checkpoint = None
        self.refresh()

    def edit_sections(self):
        if self._animating or (self.dialog and self.dialog.winfo_exists()):
            return
        dialog = self.dialog = ctk.CTkToplevel(self.root)
        dialog.title('Your study path')
        dialog.geometry('520x520')
        dialog.transient(self.root)
        dialog.grab_set()
        self.text(dialog, 'Your study path.', 24, True).pack(anchor='w', padx=25, pady=(25, 8))
        self.text(dialog, 'One section per line: start page, section name', 11, color=MUTED).pack(anchor='w', padx=25, pady=(0, 15))
        editor = ctk.CTkTextbox(dialog, corner_radius=12, font=ctk.CTkFont(family=FONT_FAMILY, size=12))
        editor.pack(fill='both', expand=True, padx=25, pady=10)
        editor.insert('1.0', '\n'.join(f"{section['start'] + 1}, {section['title']}" for section in self.session.deck['sections']))
        def save_sections():
            try:
                entries = []
                for line in editor.get('1.0', 'end').strip().splitlines():
                    number, title = line.split(',', 1)
                    entries.append((int(number) - 1, title.strip()))
                count = len(self.session.deck['slides'])
                if not entries or entries[0][0] != 0 or any(not title or page < 0 or page >= count or (i and page <= entries[i - 1][0]) for i, (page, title) in enumerate(entries)):
                    raise ValueError('Start at page 1, name each section, and use increasing page numbers.')
                self.session.deck['sections'] = [{'id': f'section-{i}', 'title': title, 'start': page, 'end': (entries[i + 1][0] if i + 1 < len(entries) else count) - 1} for i, (page, title) in enumerate(entries)]
                self.session = StudySession(self.session.deck)
                self.save()
                dialog.destroy()
                self.refresh()
            except (ValueError, IndexError) as exc:
                messagebox.showerror('Check your sections', str(exc), parent=dialog)
        self.button(dialog, 'Save my study path', save_sections, BLUE, 'white').pack(fill='x', padx=25, pady=(12, 25))

    def close(self):
        self._closed = True
        for identifier in tuple(self._scheduled):
            self.root.after_cancel(identifier)
        self._scheduled.clear()
        self.executor.shutdown(wait=False, cancel_futures=True)
        self.audio.close()
        self._photo = None
        self.root.destroy()


def main():
    root = ctk.CTk()
    NoteThat(root)
    root.mainloop()


if __name__ == '__main__':
    main()
