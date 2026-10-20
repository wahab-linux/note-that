import io
import struct
import wave

import pytest

from server.audio import DesktopAudio, make_sound
from server.study import LibraryStore, StudySession, demo_deck


def test_section_locking_checkpoint_review_and_undo():
    session = StudySession(demo_deck())
    assert session.first_incomplete == 0
    assert session.classify('revisit') == 'swipe'
    assert len(session.saved) == 1
    assert session.undo() and not session.saved
    assert session.classify('revisit') == 'swipe'
    for _ in range(3):
        assert session.classify('confident') == 'swipe'
    assert session.classify('confident') == 'section'
    assert session.section_index == 0 and session.slide is None
    session.review()
    assert session.slide['id'] == 'demo-0'
    assert session.classify('confident') == 'review'
    assert not session.saved
    session.continue_studying()
    session.continue_studying()
    assert session.section_index == 1 and session.slide['id'] == 'demo-5'


def test_whole_document_completion_and_invalid_decisions():
    session = StudySession(demo_deck())
    with pytest.raises(ValueError):
        session.classify('unknown')
    events = []
    for _ in range(18):
        if session.slide is None:
            session.continue_studying()
        events.append(session.classify('confident'))
    assert events.count('section') == 3
    assert events.count('document') == 1
    assert session.first_incomplete is None
    assert session.slide is None


def test_native_library_round_trip_and_corrupt_file_protection(tmp_path):
    store = LibraryStore(tmp_path)
    store.decks[0]['decisions']['demo-0'] = 'revisit'
    store.preferences['volume'] = .6
    store.save()
    restored = LibraryStore(tmp_path)
    assert restored.decks[0]['decisions']['demo-0'] == 'revisit'
    assert restored.preferences['volume'] == .6
    store.path.write_text('corrupt original', encoding='utf-8')
    broken = LibraryStore(tmp_path)
    assert broken.warning
    with pytest.raises(OSError):
        broken.save()
    assert store.path.read_text() == 'corrupt original'


@pytest.mark.parametrize('kind', ['confident', 'revisit', 'section', 'document', 'preview'])
def test_generated_audio_has_a_smooth_envelope_and_no_clipping(kind):
    with wave.open(io.BytesIO(make_sound(kind)), 'rb') as stream:
        assert stream.getframerate() == 22050 and stream.getnchannels() == 1
        raw = stream.readframes(stream.getnframes())
        samples = struct.unpack(f'<{len(raw) // 2}h', raw)
    assert max(map(abs, samples)) > 300
    assert max(map(abs, samples)) < 31000
    assert abs(samples[0]) < 20
    assert abs(samples[-1]) < 60


def test_audio_playback_with_dummy_output(monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    audio = DesktopAudio()
    audio.play('section', .35)
    assert not audio.error
    assert audio.mixer and audio.mixer.get_busy()
    audio.stop()
    assert not audio.mixer.get_busy()
    audio.close()
