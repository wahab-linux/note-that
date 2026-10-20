"""A quiet, slide-first native reader. Run: python desktop.py."""
from __future__ import annotations

import base64
import io
import os
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tkinter import Canvas, filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFont, ImageTk

from server.audio import DesktopAudio
from server.documents import MAX_BYTES, import_document
from server.study import LibraryStore, StudySession

BG = ('#ECEEF1', '#111315')
SURFACE = ('#FAFAF9', '#1B1D20')
INK = ('#202322', '#F1F2ED')
MUTED = ('#737976', '#929993')
SOFT = ('#EEEFEA', '#272B27')
ACCENT = ('#405E46', '#B8D6A1')
SELECTED = ('#E7ECDF', '#303B2D')
FONT_FAMILY = 'Segoe UI' if os.name == 'nt' else 'Arial'


def font(size=18, bold=False):
    candidates = [Path(os.getenv('WINDIR', 'C:/Windows')) / 'Fonts' / ('segoeuib.ttf' if bold else 'segoeui.ttf'),
                  Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
                  Path('/System/Library/Fonts/Supplemental/Arial.ttf')]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default(size=size)


class ReaderSession(StudySession):
    """Free section navigation, uninterrupted swipes, and a persistent cursor."""
    def __init__(self, deck):
        super().__init__(deck)
        first = next((i for i, slide in enumerate(deck['slides']) if slide['id'] not in deck['decisions']), 0)
        self.index = max(0, min(int(deck.get('desktop_page', first)), len(deck['slides'])))

    @property
    def slide(self):
        return self.deck['slides'][self.index] if self.index < len(self.deck['slides']) else None

    @property
    def section_index(self):
        page = min(self.index, len(self.deck['slides']) - 1)
        return next(i for i, section in enumerate(self.deck['sections']) if section['start'] <= page <= section['end'])

    def classify(self, decision):
        if decision not in {'confident', 'revisit'}:
            raise ValueError('Unknown swipe decision')
        if self.slide is None:
            return None
        identifier = self.slide['id']
        self.history.append((self.index, identifier, self.deck['decisions'].get(identifier)))
        self.history = self.history[-100:]
        self.deck['decisions'][identifier] = decision
        old_section = self.section_index
        self.index += 1
        self.deck['desktop_page'] = self.index
        return 'document' if self.slide is None else 'section' if self.section_index != old_section else 'swipe'

    def undo(self):
        if not self.history:
            return False
        self.index, identifier, previous = self.history.pop()
        if previous is None:
            self.deck['decisions'].pop(identifier, None)
        else:
            self.deck['decisions'][identifier] = previous
        self.deck['desktop_page'] = self.index
        return True

    def jump(self, index):
        self.index = self.deck['sections'][index]['start']
        self.deck['desktop_page'] = self.index
        self.history.clear()


class NoteThat:
    def __init__(self, root, data_directory=None):
        self.root = root
        self.store = LibraryStore(data_directory)
        self.preferences = self.store.preferences
        ctk.set_appearance_mode('dark' if self.preferences['dark'] else 'light')
        self.audio = DesktopAudio()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self._closed = self._animating = self._importing = False
        self._drag_start = None
        self._drag_offset = 0
        self._photo = self._base = None
        self._scheduled = set()
        self._resize_after = None
        self._fullscreen = False
        self._page_cache = None
        self._section_signature = None
        self.session = ReaderSession(next((d for d in self.store.decks if d['id'] == self.store.selected), self.store.decks[0]))
        root.title('note that')
        width = min(1920, round(root.winfo_screenwidth() * .94))
        height = min(1080, round(root.winfo_screenheight() * .9))
        root.geometry(f'{width}x{height}')
        root.minsize(900, 600)
        root.configure(fg_color=BG)
        root.grid_rowconfigure(0, weight=1)
        root.grid_columnconfigure(1, weight=1)
        root.protocol('WM_DELETE_WINDOW', self.close)
        self.build()
        for key, action in [('<Left>', lambda: self.decide('confident')), ('<Right>', lambda: self.decide('revisit')),
                            ('<Key-z>', self.undo), ('<Key-Z>', self.undo), ('<Control-o>', self.choose_file),
                            ('<Control-O>', self.choose_file), ('<F11>', self.toggle_fullscreen), ('<Escape>', self.leave_fullscreen)]:
            root.bind(key, lambda event, action=action: action())
        root.bind('<FocusOut>', self.cancel_drag, add='+')
        self.set_status(self.store.warning)
        self.later(40, self.refresh)

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

    def text(self, parent, text='', size=12, bold=False, color=INK, **kwargs):
        return ctk.CTkLabel(parent, text=text, font=ctk.CTkFont(family=FONT_FAMILY, size=size, weight='bold' if bold else 'normal'), text_color=color, **kwargs)

    def button(self, parent, text, command, **kwargs):
        defaults = dict(height=40, corner_radius=8, fg_color='transparent', hover_color=SOFT,
                        text_color=INK, anchor='w', font=ctk.CTkFont(family=FONT_FAMILY, size=13))
        defaults.update(kwargs)
        return ctk.CTkButton(parent, text=text, command=command, **defaults)

    def build(self):
        self.sidebar = side = ctk.CTkFrame(self.root, width=244, corner_radius=0, fg_color=SURFACE)
        side.grid(row=0, column=0, sticky='nsew')
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)
        side.grid_rowconfigure(5, weight=1)
        brand = ctk.CTkFrame(side, fg_color='transparent')
        brand.grid(row=0, column=0, padx=24, pady=(30, 34), sticky='ew')
        self.text(brand, 'note that', 26, True).pack(side='left')
        self.text(brand, '●', 12, color=ACCENT).pack(side='right')
        self.import_button = self.button(side, '+   Open file', self.choose_file, fg_color=INK, text_color=SURFACE, hover_color=('#363C36', '#D6DBCF'), height=44)
        self.import_button.grid(row=1, column=0, padx=20, sticky='ew')
        self.document_picker = ctk.CTkOptionMenu(side, values=[''], command=self.select_document,
            fg_color=SOFT, button_color=SOFT, button_hover_color=SELECTED, text_color=INK,
            dropdown_fg_color=SURFACE, dropdown_hover_color=SOFT, dropdown_text_color=INK,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), height=34, corner_radius=7, dynamic_resizing=False)
        self.document_picker.grid(row=2, column=0, padx=20, pady=(14, 28), sticky='ew')
        self.text(side, 'SECTIONS', 10, True, MUTED).grid(row=3, column=0, padx=25, sticky='w')
        self.document_meta = self.text(side, size=11, color=MUTED, anchor='w')
        self.document_meta.grid(row=4, column=0, padx=25, pady=(2, 13), sticky='ew')
        self.path_buttons = ctk.CTkScrollableFrame(side, fg_color='transparent', corner_radius=0,
            scrollbar_button_color=SOFT, scrollbar_button_hover_color=MUTED)
        self.path_buttons.grid(row=5, column=0, padx=(14, 8), sticky='nsew')
        self.section_buttons = []
        footer = ctk.CTkFrame(side, fg_color='transparent')
        footer.grid(row=6, column=0, padx=24, pady=(16, 22), sticky='ew')
        self.page_label = self.text(footer, size=12, bold=True, color=ACCENT)
        self.page_label.pack(anchor='w', pady=(0, 10))
        self.progress = ctk.CTkProgressBar(footer, progress_color=ACCENT, fg_color=SOFT, height=3)
        self.progress.pack(fill='x')
        self.text(footer, 'Left: know it  /  Right: save it', 11, color=MUTED).pack(anchor='w', pady=(15, 3))
        self.text(footer, 'Drag to swipe · Z to undo · F11 full screen', 9, color=MUTED).pack(anchor='w')
        options = ctk.CTkFrame(footer, fg_color='transparent')
        options.pack(fill='x', pady=(20, 0))
        self.dark_var = ctk.BooleanVar(value=self.preferences['dark'])
        self.theme_toggle = ctk.CTkSwitch(options, text='Dark mode', variable=self.dark_var, command=self.toggle_theme,
            width=130, switch_width=32, switch_height=18, progress_color=ACCENT,
            font=ctk.CTkFont(family=FONT_FAMILY, size=12), text_color=INK)
        self.theme_toggle.pack(side='left')
        self.sound_button = self.button(options, '', self.toggle_sound, width=38, height=34, anchor='center',
            font=ctk.CTkFont(family='Segoe UI Emoji' if os.name == 'nt' else 'DejaVu Sans', size=20))
        self.sound_button.pack(side='right')
        self._sound_icons = {}
        for enabled, name in [(True, 'sound-on'), (False, 'sound-off')]:
            with Image.open(Path(__file__).parent / 'data' / 'native' / f'{name}.png') as image:
                self._sound_icons[enabled] = ctk.CTkImage(image.copy(), size=(26, 26))
        self.status = self.text(footer, size=10, color=MUTED, anchor='w', justify='left', wraplength=192)
        self.status.pack(fill='x', pady=(8, 0))
        self.canvas = Canvas(self.root, width=800, height=600, highlightthickness=0, bd=0, bg=self.color(BG), cursor='hand2')
        self.canvas.grid(row=0, column=1, sticky='nsew')
        self.image_item = self.canvas.create_image(0, 0, anchor='center')
        self.canvas.bind('<Configure>', self.schedule_resize)
        self.canvas.bind('<ButtonPress-1>', self.drag_start)
        self.canvas.bind('<B1-Motion>', self.drag_move)
        self.canvas.bind('<ButtonRelease-1>', self.drag_end)
        self.update_sound_label()
        self.update_documents()

    def color(self, pair):
        return pair[1 if self.preferences['dark'] else 0] if isinstance(pair, tuple) else pair

    def set_status(self, message=''):
        self.status.configure(text=message)

    def save(self):
        try:
            self.store.save()
            return True
        except OSError as exc:
            self.set_status(f'Could not save: {exc}')
            return False

    def update_sound_label(self):
        self.sound_button.configure(image=self._sound_icons[bool(self.preferences['sound'])])

    def toggle_sound(self):
        self.preferences['sound'] = not self.preferences['sound']
        self.update_sound_label()
        if self.preferences['sound']:
            self.play('preview')
        else:
            self.audio.stop()
        self.save()

    def toggle_theme(self):
        self.preferences['dark'] = not self.preferences['dark']
        self.dark_var.set(self.preferences['dark'])
        ctk.set_appearance_mode('dark' if self.preferences['dark'] else 'light')
        self.canvas.configure(bg=self.color(BG))
        self.save()
        self.draw_if_idle()

    def toggle_fullscreen(self):
        self._fullscreen = not self._fullscreen
        self.root.attributes('-fullscreen', self._fullscreen)

    def leave_fullscreen(self):
        self._fullscreen = False
        self.root.attributes('-fullscreen', False)
        self.cancel_drag()

    def play(self, kind):
        if self.preferences['sound']:
            self.audio.play(kind, self.preferences['volume'])
            if self.audio.error:
                self.set_status(self.audio.error)

    def choose_file(self):
        if self._importing:
            return
        filename = filedialog.askopenfilename(parent=self.root, title='Open slides', filetypes=[('Slides', '*.pdf *.pptx *.png *.jpg *.jpeg *.webp'), ('All files', '*.*')])
        if filename:
            self.import_file(Path(filename))

    def import_file(self, path):
        if self._importing:
            return
        self._importing = True
        self.import_button.configure(state='disabled', text='Opening…')
        self.set_status(f'Opening {path.name}…')
        def load():
            if path.stat().st_size > MAX_BYTES:
                raise ValueError('Choose a file under 100 MB.')
            return import_document(path.name, path.read_bytes())
        future = self.executor.submit(load)
        def poll():
            if not future.done() or self._animating:
                self.later(50, poll)
                return
            self._importing = False
            self.import_button.configure(state='normal', text='+   Open file')
            try:
                deck = future.result()
                self.store.decks.append(deck)
                self.select_deck(deck['id'])
                self.set_status('PPTX shows text. Open a PDF for original slide layouts.' if deck['kind'] == 'pptx' else '')
            except Exception as exc:
                self.set_status(str(exc))
                messagebox.showerror('Could not open file', str(exc), parent=self.root)
        self.later(50, poll)

    def update_documents(self):
        self._documents = {f'{i + 1}. {deck["title"][:24]}': deck['id'] for i, deck in enumerate(self.store.decks)}
        self.document_picker.configure(values=list(self._documents))
        self.document_picker.set(next(label for label, identifier in self._documents.items() if identifier == self.session.deck['id']))

    def select_document(self, label):
        self.select_deck(self._documents[label])

    def select_deck(self, identifier):
        if self._animating:
            self.update_documents()
            return
        self.cancel_drag()
        self.store.selected = identifier
        self.session = ReaderSession(next(d for d in self.store.decks if d['id'] == identifier))
        self._page_cache = None
        self.update_documents()
        self.set_status()
        self.save()
        self.refresh()

    def refresh(self):
        if self._closed:
            return
        deck = self.session.deck
        self.document_meta.configure(text=f'{len(deck["slides"])} slides')
        self.page_label.configure(text=f'{min(self.session.index + 1, len(deck["slides"])):02} / {len(deck["slides"]):02}' + ('  ·  Finished' if self.session.slide is None else ''))
        self.progress.set(self.session.index / len(deck['slides']))
        signature = (deck['id'], tuple((s['title'], s['start'], s['end']) for s in deck['sections']))
        if signature != self._section_signature:
            self._section_signature = signature
            for child in self.path_buttons.winfo_children():
                child.destroy()
            self.section_buttons = []
            for index, section in enumerate(deck['sections']):
                label = f'{index + 1:02}   {section["title"][:22]}\n       {section["start"] + 1} - {section["end"] + 1}'
                button = self.button(self.path_buttons, label, lambda i=index: self.visit_section(i), height=58)
                button.pack(fill='x', pady=3)
                self.section_buttons.append(button)
        for index, button in enumerate(self.section_buttons):
            active = self.session.slide is not None and index == self.session.section_index
            button.configure(fg_color=SELECTED if active else 'transparent', text_color=ACCENT if active else MUTED)
        self.draw_slide()

    def visit_section(self, index):
        if self._animating:
            return
        self.cancel_drag()
        self.session.jump(index)
        self.save()
        self.refresh()

    @staticmethod
    def lines(draw, text, chosen_font, width):
        lines = []
        for paragraph in text.split('\n'):
            line = ''
            for word in paragraph.split():
                if line and draw.textlength(line + ' ' + word, font=chosen_font) <= width:
                    line += ' ' + word
                    continue
                if line:
                    lines.append(line)
                    line = ''
                for character in word:
                    if line and draw.textlength(line + character, font=chosen_font) > width:
                        lines.append(line)
                        line = ''
                    line += character
            lines.append(line)
        return lines

    def make_card(self):
        width, height = max(200, self.canvas.winfo_width()), max(200, self.canvas.winfo_height())
        margin = max(12, min(32, round(width * .02)))
        available = (width - margin * 2, height - margin * 2)
        slide = self.session.slide
        if slide and slide.get('image'):
            key = (self.session.deck['id'], slide['id'])
            if self._page_cache is None or self._page_cache[0] != key:
                with Image.open(io.BytesIO(base64.b64decode(slide['image'].split(',', 1)[1]))) as source:
                    self._page_cache = (key, source.convert('RGB'))
            page = self._page_cache[1]
            scale = min(available[0] / page.width, available[1] / page.height)
            return page.resize((max(1, round(page.width * scale)), max(1, round(page.height * scale))), Image.Resampling.LANCZOS)
        card_width = available[0]
        card_height = min(available[1], round(card_width * 9 / 16))
        image = Image.new('RGB', (card_width, card_height), self.color(SURFACE))
        draw = ImageDraw.Draw(image)
        pad = round(card_width * .065)
        usable = card_width - pad * 2
        if slide:
            title, body = slide['title'], slide.get('body', '')
            kicker = slide.get('kicker', self.session.section['title']).upper()
        else:
            title, body, kicker = 'A little more familiar.', 'All slides explored. Pick any section to take another look.', 'SESSION COMPLETE'
        title_size = min(64, max(24, round(card_width * .042)))
        body_size = min(28, max(14, round(card_width * .019)))
        while True:
            title_font, body_font = font(title_size, True), font(body_size)
            titles = self.lines(draw, title, title_font, usable)
            bodies = self.lines(draw, body, body_font, usable)
            title_step, body_step = round(title_size * 1.25), round(body_size * 1.55)
            total = len(titles) * title_step + len(bodies) * body_step + 40
            if total <= card_height - pad * 2 - 38 or body_size <= 8:
                break
            title_size = max(16, title_size - 2)
            body_size -= 1
        draw.text((pad, pad), kicker[:72], font=font(max(10, round(card_width * .009)), True), fill=self.color(ACCENT))
        y = max(pad + 40, (card_height - total) // 2 + 18)
        for line in titles:
            draw.text((pad, y), line, font=title_font, fill=self.color(INK))
            y += title_step
        y += 22
        for line in bodies:
            draw.text((pad, y), line, font=body_font, fill=self.color(MUTED))
            y += body_step
        return image

    def schedule_resize(self, event=None):
        if self._resize_after:
            self.root.after_cancel(self._resize_after)
            self._scheduled.discard(self._resize_after)
        self._resize_after = self.later(90, self.draw_if_idle)

    def draw_if_idle(self):
        self._resize_after = None
        if not self._animating:
            self.cancel_drag()
            self.draw_slide()

    def draw_slide(self):
        if self._closed:
            return
        self._base = self.make_card()
        self._photo = ImageTk.PhotoImage(self._base, master=self.root)
        self.canvas.itemconfigure(self.image_item, image=self._photo)
        self.paint()

    def paint(self, offset=0):
        # Move the existing Tk image, rather than upload a 1080p bitmap per frame.
        self.canvas.coords(self.image_item, self.canvas.winfo_width() / 2 + offset, self.canvas.winfo_height() / 2)

    def drag_start(self, event):
        if not self._animating and self.session.slide:
            self.canvas.focus_set()
            self._drag_start = (event.x, event.y)
            self._drag_offset = 0
            self._drag_sample = (event.x, time.perf_counter())
            self._velocity = 0
            self.canvas.configure(cursor='fleur')

    def drag_move(self, event):
        if self._drag_start is None:
            return
        now = time.perf_counter()
        last_x, last_time = self._drag_sample
        self._velocity = (event.x - last_x) / max(.001, now - last_time)
        self._drag_sample = (event.x, now)
        self._drag_offset = (event.x - self._drag_start[0]) * 1.65
        if not self.preferences['reduced_motion']:
            self.paint(self._drag_offset)

    @property
    def swipe_threshold(self):
        return max(28, min(44, self.canvas.winfo_width() * .025))

    def drag_end(self, event):
        if self._drag_start is None:
            return
        dx, dy = event.x - self._drag_start[0], event.y - self._drag_start[1]
        recent = time.perf_counter() - self._drag_sample[1] < .09
        flick = recent and abs(dx) >= 16 and abs(self._velocity) >= 650 and dx * self._velocity > 0
        self._drag_start = None
        self.canvas.configure(cursor='hand2')
        if abs(dx) > abs(dy) * 1.15 and (abs(dx) >= self.swipe_threshold or flick):
            self.decide('revisit' if dx > 0 else 'confident')
        else:
            self.animate_to(0)

    def cancel_drag(self, event=None):
        if event is not None and event.widget != self.root:
            return
        if self._drag_start is not None:
            self._drag_start = None
            self._drag_offset = 0
            self.canvas.configure(cursor='hand2')
            self.paint()

    def animate_to(self, target, finished=None, duration=.14):
        if self.preferences['reduced_motion']:
            self.paint(target)
            self._drag_offset = target
            self._animating = False
            if finished:
                finished()
            return
        self._animating = True
        start, offset = time.perf_counter(), self._drag_offset
        def frame():
            elapsed = min(1, (time.perf_counter() - start) / duration)
            self.paint(offset + (target - offset) * (1 - (1 - elapsed) ** 3))
            if elapsed < 1:
                self.later(12, frame)
            else:
                self._drag_offset = target
                self._animating = False
                if finished:
                    finished()
        frame()

    def decide(self, decision):
        if self._animating or self.session.slide is None:
            return
        if self._base is None:
            self.draw_slide()
        self._drag_start = None
        self.canvas.configure(cursor='hand2')
        direction = 1 if decision == 'revisit' else -1
        def advance():
            milestone = self.session.classify(decision)
            self.save()
            self.refresh()
            self.play(milestone if milestone in {'section', 'document'} else decision)
            self._drag_offset = -direction * 36
            self.animate_to(0, duration=.1)
        self.animate_to(direction * (self.canvas.winfo_width() + self._base.width) / 2, advance)

    def undo(self):
        if not self._animating and self.session.undo():
            self.cancel_drag()
            self.save()
            self.refresh()

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
