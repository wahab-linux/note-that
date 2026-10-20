import gc
import os
import time

import customtkinter as ctk
import pymupdf
import pytest
from PIL import Image, ImageChops, ImageTk

from desktop import BG, NoteThat, ReaderSession, ShakeGesture
from server.study import LibraryStore, demo_deck


def pump(root, condition=lambda: True, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        root.update()
        if condition():
            return
        time.sleep(.005)
    raise AssertionError('Native UI did not become ready in time')


@pytest.fixture
def native(tmp_path, monkeypatch):
    if not os.environ.get('DISPLAY'):
        pytest.skip('Native UI tests require a display or Xvfb.')
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    gc.collect()  # Finalize prior Tk windows on the UI thread, never an import worker.
    root = ctk.CTk()
    failures = []
    root.report_callback_exception = lambda kind, error, traceback: failures.append(str(error))
    app = NoteThat(root, tmp_path)
    root.geometry('1920x1080')
    pump(root, lambda: app._base is not None and app.canvas.winfo_width() > 1600)
    yield app
    app.close()
    assert not failures
    del app
    del root
    gc.collect()


def test_reader_crosses_sections_without_a_checkpoint_and_undo_restores_cursor():
    session = ReaderSession(demo_deck())
    for _ in range(4):
        session.classify('confident')
    assert session.classify('revisit') == 'section'
    assert session.slide['id'] == 'demo-5'
    assert session.section_index == 1
    assert session.undo()
    assert session.slide['id'] == 'demo-4'
    assert 'demo-4' not in session.deck['decisions']
    assert not session.saved
    session.classify('confident')
    assert ReaderSession(session.deck).index == 5


def test_reader_can_open_any_section_and_restore_previous_decision():
    session = ReaderSession(demo_deck())
    session.classify('revisit')
    session.jump(0)
    session.classify('confident')
    session.undo()
    assert session.deck['decisions']['demo-0'] == 'revisit'
    session.jump(3)
    assert session.index == 14
    assert session.slide['id'] == 'demo-14'
    while session.slide:
        milestone = session.classify('confident')
    assert milestone == 'document'
    assert ReaderSession(session.deck).slide is None
    session.undo()
    assert session.slide['id'] == 'demo-17'


def test_reader_resumes_legacy_progress():
    deck = demo_deck()
    deck['decisions'] = {'demo-0': 'confident', 'demo-1': 'revisit'}
    assert ReaderSession(deck).index == 2


def test_saved_review_keeps_reading_position_and_updates_saved_slides():
    session = ReaderSession(demo_deck())
    session.classify('revisit')
    session.classify('confident')
    session.classify('revisit')
    session.review_saved()
    assert session.slide['id'] == 'demo-0'
    session.classify('confident')
    assert [s['id'] for s in session.saved] == ['demo-2']
    assert session.slide['id'] == 'demo-2'
    session.undo()
    assert session.slide['id'] == 'demo-0'
    assert len(session.saved) == 2
    session.review_saved('demo-2')
    assert session.slide['id'] == 'demo-2'
    session.classify('revisit')
    assert session.slide is None
    assert session.index == session.deck['desktop_page'] == 3
    session.leave_review()
    assert session.slide['id'] == 'demo-3'
    session.review_saved()
    session.jump(1)
    assert session.review_ids is None
    assert session.index == 5


def test_shake_requires_fast_substantial_horizontal_reversals():
    shake = ShakeGesture(400, 300, 0)
    assert not shake.update(460, 300, .1)
    assert not shake.update(340, 300, .2)
    assert not shake.update(460, 300, .3)
    assert shake.update(340, 300, .4)
    for pattern in [[(460, 300), (450, 300), (460, 300), (450, 300)],  # Tiny jitter.
                    [(460, 410), (340, 520), (460, 630), (340, 740)]]:  # Vertical movement.
        shake = ShakeGesture(400, 300, 0)
        assert not any(shake.update(x, y, (i + 1) * .1) for i, (x, y) in enumerate(pattern))
    shake = ShakeGesture(400, 300, 0)
    assert not any(shake.update(x, 300, (i + 1) * .5) for i, x in enumerate([460, 340, 460, 340]))


def drag(app, dx, dy=0):
    app.canvas.event_generate('<ButtonPress-1>', x=400, y=300)
    app.canvas.event_generate('<B1-Motion>', x=400 + dx, y=300 + dy)
    app.canvas.event_generate('<ButtonRelease-1>', x=400 + dx, y=300 + dy)
    pump(app.root, lambda: not app._animating)


def test_native_short_drags_flicks_clicks_vertical_motion_and_cancel(native):
    app = native
    app.preferences['reduced_motion'] = True
    drag(app, 45)
    assert app.session.index == 1
    assert len(app.session.saved) == 1
    drag(app, -45)
    assert app.session.index == 2
    assert app.session.deck['decisions']['demo-1'] == 'confident'
    drag(app, 0)
    drag(app, 7)
    drag(app, 45, 120)
    assert app.session.index == 2
    drag(app, 20)  # A quick flick below the ordinary distance threshold.
    assert app.session.index == 3
    app.canvas.event_generate('<ButtonPress-1>', x=400, y=300)
    app.canvas.event_generate('<B1-Motion>', x=470, y=300)
    app.cancel_drag()
    app.canvas.event_generate('<ButtonRelease-1>', x=470, y=300)
    assert app.session.index == 3
    app.undo()
    assert app.session.index == 2
    assert app.canvas.coords(app.image_item)[0] == app.canvas.winfo_width() / 2


def test_native_large_canvas_and_animated_swipe(native):
    app = native
    assert app.sidebar.winfo_width() == 244
    assert app.canvas.winfo_width() == 1676
    assert app.canvas.winfo_height() == 1080
    assert app._base.width > 1600
    assert not hasattr(app, 'know_button')
    assert not hasattr(app, 'later_button')
    photo = app._photo
    app.canvas.event_generate('<ButtonPress-1>', x=400, y=300)
    app.canvas.event_generate('<B1-Motion>', x=450, y=300)
    assert app._photo is photo  # Dragging moves the bitmap without re-uploading it.
    app.canvas.event_generate('<ButtonRelease-1>', x=450, y=300)
    assert app._animating
    app.decide('confident')  # Ignore duplicate input during the outgoing animation.
    pump(app.root, lambda: not app._animating)
    assert app.session.index == 1
    assert len(app.session.deck['decisions']) == 1
    app.visit_section(3)
    assert app.session.index == 14


def test_native_real_pdf_fit_theme_sound_and_resume(native, tmp_path):
    app = native
    app.preferences['reduced_motion'] = True
    path = tmp_path / 'Wide slides.pdf'
    with pymupdf.open() as pdf:
        for i in range(2):
            page = pdf.new_page(width=1920, height=1080)
            page.insert_text((100, 180), f'Full size slide {i + 1}', fontsize=64)
        pdf.save(path)
    app.import_file(path)
    pump(app.root, lambda: not app._importing)
    assert app.session.deck['kind'] == 'pdf'
    assert app._base.width > 1600
    assert abs(app._base.width / app._base.height - 16 / 9) < .01
    assert app._base.height < app.canvas.winfo_height()
    app.toggle_theme()
    assert app.preferences['dark']
    assert app.canvas.cget('bg') == BG[1]
    app.sound_button.invoke()
    assert app.preferences['sound']
    assert app.sound_button.cget('image') is app._sound_icons[True]
    assert app.audio.mixer and not app.audio.error
    app.sound_button.invoke()
    assert not app.preferences['sound']
    assert app.sound_button.cget('image') is app._sound_icons[False]
    app.decide('revisit')
    loaded = LibraryStore(tmp_path)
    assert loaded.preferences['dark']
    assert not loaded.preferences['sound']
    assert loaded.selected == app.session.deck['id']
    restored = ReaderSession(next(d for d in loaded.decks if d['id'] == loaded.selected))
    assert restored.index == 1
    app.decide('confident')
    assert app.session.slide is None
    app.visit_section(0)
    assert app.session.index == 0
    app.root.geometry('1000x650')
    pump(app.root, lambda: app.canvas.winfo_width() < 800)
    pump(app.root, lambda: app._base.width < 800)
    assert app._base.height <= app.canvas.winfo_height()
    assert app.sound_button.winfo_ismapped()
    assert app.theme_toggle.winfo_ismapped()


def test_native_hide_show_panel_preserves_swipes_and_remembers_choice(native, tmp_path):
    app = native
    app.preferences['reduced_motion'] = True
    app.panel_button.invoke()
    pump(app.root, lambda: app.canvas.winfo_width() == 1920)
    assert not app.sidebar.winfo_ismapped()
    assert app.panel_button.winfo_ismapped()
    assert app.panel_button.cget('text') == 'Show panel'
    assert app._base.width > 1800
    drag(app, 50)
    assert app.session.index == 1
    assert LibraryStore(tmp_path).preferences['sidebar_hidden']
    app.panel_button.invoke()
    pump(app.root, lambda: app.canvas.winfo_width() == 1676)
    assert app.sidebar.winfo_ismapped()
    assert app.panel_button.cget('text') == 'Hide panel'
    assert app.session.index == 1
    assert not LibraryStore(tmp_path).preferences['sidebar_hidden']


def test_native_saved_button_count_browsing_and_empty_state(native):
    app = native
    app.preferences['reduced_motion'] = True
    app.saved_button.invoke()
    assert app.session.slide is None
    assert not app.section_buttons
    app.saved_button.invoke()
    app.decide('revisit')
    app.decide('confident')
    app.decide('revisit')
    assert app.saved_button.cget('text') == 'Saved for later (2)'
    app.saved_button.invoke()
    assert len(app.section_buttons) == 2
    assert app.path_heading.cget('text') == 'SAVED FOR LATER'
    assert app.session.slide['id'] == 'demo-0'
    app.section_buttons[1].invoke()
    assert app.session.slide['id'] == 'demo-2'
    app.decide('confident')
    assert app.saved_button.cget('text') == 'Saved for later (1)'
    assert len(app.section_buttons) == 1
    app.undo()
    assert app.saved_button.cget('text') == 'Saved for later (2)'
    app.saved_button.invoke()
    assert app.session.slide['id'] == 'demo-3'
    assert app.path_heading.cget('text') == 'SECTIONS'


def test_native_shake_rotates_same_slide_holds_then_restores_without_saving(native):
    app = native
    app.canvas.event_generate('<ButtonPress-1>', x=400, y=300)
    for x in [460, 340, 460, 340]:
        app.canvas.event_generate('<B1-Motion>', x=x, y=300)
    app.canvas.event_generate('<ButtonRelease-1>', x=340, y=300)
    assert app._animating
    assert app._egg_phase == 'shrinking'
    pump(app.root, lambda: app._egg_phase == 'holding')
    held_at = time.monotonic()
    assert app._egg_angle == 180
    assert app._egg_scale == 1
    inverted = ImageTk.getimage(app._photo).convert('RGB')
    assert ImageChops.difference(inverted, app._base.transpose(Image.Transpose.ROTATE_180)).getbbox() is None
    app.decide('revisit')
    assert app.session.index == 0
    pump(app.root, lambda: app._egg_phase != 'holding')
    assert time.monotonic() - held_at >= .95
    pump(app.root, lambda: not app._animating)
    assert app._egg_phase == 'idle'
    assert app.session.slide['id'] == 'demo-0'
    assert not app.session.deck['decisions']
    assert ImageChops.difference(ImageTk.getimage(app._photo).convert('RGB'), app._base).getbbox() is None
    drag(app, -50)
    assert app.session.index == 1


def test_native_shake_respects_reduced_motion_without_classifying(native):
    app = native
    app.preferences['reduced_motion'] = True
    app.canvas.event_generate('<ButtonPress-1>', x=400, y=300)
    for x in [460, 340, 460, 340]:
        app.canvas.event_generate('<B1-Motion>', x=x, y=300)
    app.canvas.event_generate('<ButtonRelease-1>', x=340, y=300)
    assert not app._animating
    assert not app.session.deck['decisions']
    assert app.session.index == 0
