"""Shared, UI-independent study logic for the native Python app."""
from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def demo_deck() -> dict[str, Any]:
    return json.loads((ROOT / 'data' / 'demo.json').read_text(encoding='utf-8'))


class StudySession:
    def __init__(self, deck):
        self.deck = deck
        self.checkpoint = None
        self.review_ids = None
        self.review_index = 0
        self.history = []

    def done(self, section):
        return all(s['id'] in self.deck['decisions'] for s in self.deck['slides'][section['start']:section['end'] + 1])

    @property
    def first_incomplete(self):
        return next((i for i, s in enumerate(self.deck['sections']) if not self.done(s)), None)

    @property
    def section_index(self):
        if self.checkpoint is not None:
            return self.checkpoint
        incomplete = self.first_incomplete
        return incomplete if incomplete is not None else len(self.deck['sections']) - 1

    @property
    def section(self):
        return self.deck['sections'][self.section_index]

    @property
    def slide(self):
        if self.review_ids is not None:
            if self.review_index >= len(self.review_ids):
                return None
            return next(s for s in self.deck['slides'] if s['id'] == self.review_ids[self.review_index])
        return next((s for s in self.deck['slides'][self.section['start']:self.section['end'] + 1]
                     if s['id'] not in self.deck['decisions']), None)

    @property
    def saved(self):
        return [s for s in self.deck['slides'] if self.deck['decisions'].get(s['id']) == 'revisit']

    def classify(self, decision):
        if decision not in {'confident', 'revisit'}:
            raise ValueError('Unknown swipe decision')
        slide = self.slide
        if slide is None:
            return None
        section_index = self.section_index
        self.history.append((copy.deepcopy(self.deck), self.checkpoint, copy.copy(self.review_ids), self.review_index))
        self.history = self.history[-50:]
        self.deck['decisions'][slide['id']] = decision
        if self.review_ids is not None:
            if slide['id'] not in self.deck['revisited']:
                self.deck['revisited'].append(slide['id'])
            self.review_index += 1
            return 'review' if self.slide is None else 'swipe'
        if self.done(self.deck['sections'][section_index]):
            self.checkpoint = section_index
            return 'document' if self.first_incomplete is None else 'section'
        return 'swipe'

    def undo(self):
        if not self.history:
            return False
        previous, self.checkpoint, self.review_ids, self.review_index = self.history.pop()
        self.deck.clear()
        self.deck.update(previous)
        return True

    def continue_studying(self):
        if self.review_ids is not None:
            self.review_ids = None
            self.review_index = 0
        elif self.done(self.section):
            self.checkpoint = None
        self.history.clear()

    def review(self, ids=None):
        self.review_ids = list(ids) if ids is not None else [s['id'] for s in self.saved]
        self.review_index = 0
        self.history.clear()


class LibraryStore:
    """Atomic saves retain documents, progress, sound settings, and theme."""
    def __init__(self, directory=None):
        if directory is None:
            default = Path(os.getenv('LOCALAPPDATA', Path.home() / '.local' / 'share')) / 'NoteThat'
            directory = Path(os.getenv('NOTE_THAT_DATA_DIR', default))
        self.path = Path(directory) / 'library.json'
        self.warning = ''
        self.decks = [demo_deck()]
        self.preferences = {'sound': False, 'volume': .35, 'dark': False, 'reduced_motion': False}
        self.selected = self.decks[0]['id']
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                decks = data['decks']
                if not isinstance(decks, list) or not decks:
                    raise ValueError('Library has no documents')
                for deck in decks:
                    if not deck.get('slides') or not deck.get('sections') or not isinstance(deck.get('decisions'), dict):
                        raise ValueError('Invalid document data')
                self.decks = decks
                self.preferences.update(data.get('preferences', {}))
                self.selected = data.get('selected', self.decks[0]['id'])
            except (ValueError, OSError, KeyError, TypeError):
                self.warning = 'The saved library could not be opened. It has been kept on disk; choose another data directory to save a new library.'

    def save(self):
        if self.warning:
            raise OSError(self.warning)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps({'decks': self.decks, 'preferences': self.preferences, 'selected': self.selected}, ensure_ascii=False), encoding='utf-8')
        temporary.replace(self.path)
