import os
import time

import customtkinter as ctk
import pymupdf
import pytest

from desktop import NoteThat

pytestmark = pytest.mark.skipif(not os.environ.get('DISPLAY'), reason='Native desktop tests require a display or Xvfb.')


def pump(root, condition=lambda: True, timeout=4):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        root.update()
        if condition():
            return
        time.sleep(.01)
    raise AssertionError('Native UI did not become ready in time')


@pytest.fixture
def native(tmp_path, monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    root = ctk.CTk()
    failures = []
    root.report_callback_exception = lambda kind, error, traceback: failures.append(str(error))
    app = NoteThat(root, tmp_path)
    pump(root, lambda: app._base is not None)
    yield app
    app.close()
    assert not failures


def test_native_swipe_animation_section_confetti_review_and_save(native):
    app = native
    assert app.session.slide['id'] == 'demo-0'
    app.decide('revisit')
    assert app._animating
    pump(app.root, lambda: not app._animating)
    assert app.session.slide['id'] == 'demo-1'
    assert len(app.session.saved) == 1
    app.undo()
    assert app.session.slide['id'] == 'demo-0'
    for _ in range(5):
        app.decide('confident')
        pump(app.root, lambda: not app._animating)
    assert app.session.slide is None
    assert app.session.first_incomplete == 1
    assert app.confetti_kind == 'section'
    assert len(app.canvas.find_withtag('confetti')) > 0
    app.continue_session()
    assert app.session.slide['id'] == 'demo-5'
    assert app.store.path.exists()


def test_native_real_pdf_import_document_confetti_theme_and_sound(native, tmp_path):
    app = native
    app.preferences['reduced_motion'] = True
    app.preferences['sound'] = True
    path = tmp_path / 'A little focus.pdf'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=500, height=300)
        page.insert_text((45, 100), 'A little focus', fontsize=28)
        pdf.save(path)
    app.import_file(path)
    pump(app.root, lambda: not app._importing)
    assert app.session.deck['kind'] == 'pdf'
    assert app.session.slide['image'].startswith('data:image/webp;')
    app.decide('confident')
    assert not app._animating
    assert app.confetti_kind == 'document'
    assert app.session.first_incomplete is None
    assert app.audio.mixer and not app.audio.error
    app.toggle_theme()
    assert app.preferences['dark']
    assert app.canvas.cget('bg') == '#1B2230'
    app.sound_settings()
    app.root.update()
    assert app.dialog.winfo_exists()
    app.dialog.destroy()


def test_native_mouse_drag_and_library_navigation(native):
    app = native
    app.preferences['reduced_motion'] = True
    app.canvas.event_generate('<ButtonPress-1>', x=100, y=120)
    app.canvas.event_generate('<B1-Motion>', x=230, y=120)
    app.canvas.event_generate('<ButtonRelease-1>', x=230, y=120)
    app.root.update()
    assert len(app.session.saved) == 1
    app.start_review()
    assert app.session.slide['id'] == 'demo-0'
    app.decide('confident')
    assert not app.session.saved
    app.continue_session()
    app.show('library')
    app.root.update()
    assert app.other_view.winfo_ismapped()
    app.select_deck(app.session.deck['id'])
    app.root.update()
    assert app.study_view.winfo_ismapped()
