# note that ⚡

A little focus. One familiar slide at a time.

A PDF and slide study app, styled to match [Earl Gray](https://github.com/wahab-linux/earl-gray): a white sidebar, rounded cards, pale blue workspace, Google-color accents, light/dark mode, and a red lightning logo. Available as a **native Python desktop app** and a **browser app served by Python**.

## Native Python desktop app

Use Python 3.11 or newer, with Tk included. No Node.js or frontend build is needed for this edition.

```sh
python -m pip install -r requirements.txt
python desktop.py
```

On Windows, `py` can be used in place of `python`. Python's Windows installer includes Tk by default. On Linux, install your distribution's Tk package (often `python3-tk`) and run in a desktop session. On macOS, use a Python installation with working Tk support.

Import a PDF, PPTX, or slide image using **Add files**. Drag the card right to save a slide, left when confident, or use the arrow keys. **Z** or **Undo** reverses the last swipe. The study path locks later sections until the current one is explored; edit section names and starting pages with **Edit sections**. The library and progress screens let you resume documents and review saved slides.

**Sound off/on** opens sound settings: enable soft swipe tones and completion chimes, adjust volume, or select reduced motion. Sounds are generated locally and played with pygame. An unavailable audio device is reported without interrupting study. Confetti celebrates sections and the entire document; reduced motion keeps the congratulations and skips moving confetti.

Native documents, progress, theme, and sound settings are saved locally in `NoteThat/library.json` under `%LOCALAPPDATA%` on Windows or `~/.local/share` elsewhere. Set `NOTE_THAT_DATA_DIR` to choose another storage directory. Saves use an atomic file replacement; an unreadable existing library is preserved rather than overwritten. There are no accounts or uploads in the native app.

## Python web app

Use Python 3.11+ and Node.js 22.12+ to install and build:

```sh
python -m pip install -r requirements.txt
npm ci
npm run build
python app.py
```

The Python server listens on port **5173**. Override with `python app.py --host 127.0.0.1 --port 8000` as needed. The server serves the built interface and handles PDF, PPTX, and image import through FastAPI. Original uploads are processed without retaining a copy of the source file. The imported library and study progress are stored in the browser's IndexedDB, not on the server. They remain specific to that browser and origin; clearing browser data removes them. Native and browser libraries are separate.

For frontend hot reload, run `python app.py --port 8000` in one terminal and `npm run dev` in another. Vite forwards `/api` to Python. Restart the Vite process after reinstalling `node_modules`. Static hosting is also supported: `npm run preview` uses the browser-based importer when the Python API is absent.

The web edition uses a spring-based card transition with squash and stretch, optional Web Audio swipe sounds and chimes, volume control, and canvas confetti. Sound starts muted and remembers your preferences. Operating-system reduced-motion settings disable moving confetti and simplify card transitions. No third-party audio or analytics requests are used.

## Documents and sections

- PDF pages preserve their original appearance. Top-level PDF bookmarks become sections. Documents without bookmarks are grouped into five-slide sections, which you can edit.
- PowerPoint imports **text cards** in presentation order; its visual layouts, diagrams, and images are not reproduced. Export to PDF for original slide designs. Legacy `.ppt` files are not supported.
- Import limits are **100 MB per file**, **300 PDF pages or PowerPoint slides**, and **40 megapixels per image** in the Python importer. Password-protected PDFs must be unlocked before import.
- Each section ends at a checkpoint with a chance to revisit saved slides or continue. Saved slides stay in the revisit pile until you mark them confident.
- An included 18-slide demo makes the study flow available immediately. Both editions use the same demo content.

The server is intended for local development or a trusted private environment. It provides no authentication layer for public multi-user hosting.

## Validation

```sh
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_python.py tests/test_study.py -q
```

Run native UI tests with a desktop display:

```sh
python -m pytest tests/test_desktop.py -q
```

On headless Linux, use `xvfb-run -a python -m pytest tests/test_desktop.py -q`. These tests explicitly skip when no display is available. Audio playback tests use SDL's dummy audio output; generated WAV samples are checked for audible signal, envelope continuity, and clipping.

Browser integration tests run against the Python server on port 5174:

```sh
npm run build
npx playwright install chromium
npm test
```

Set `CHROMIUM_EXECUTABLE_PATH` to use an existing compatible Chromium installation. The suite covers document import through Python, PDF rendering and sections, saved progress, undo, revisit sessions, actual audio-node playback, mute/volume persistence, confetti for a real PDF, theme persistence, reduced motion, and phone swipes. Windows executable packaging and physical audio-device output have not been validated in this Linux cloud environment.
