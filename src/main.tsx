import React, { useCallback, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import {
  ArrowLeft,
  ArrowRight,
  ArrowUpRight,
  Bookmark,
  BookOpen,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileText,
  FolderOpen,
  Keyboard,
  Layers3,
  LockKeyhole,
  MoreHorizontal,
  Plus,
  RotateCcw,
  Search,
  Settings2,
  Sparkles,
  Trash2,
  Upload,
  Volume2,
  VolumeX,
  Sun,
  Moon,
  ShieldCheck,
  X,
} from "lucide-react";
import {
  demoDeck,
  deleteDeck,
  loadDecks,
  nextSection,
  saveDeck,
  sectionDone,
  type Deck,
  type Decision,
  type Slide,
} from "./model";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import {
  Celebration,
  JellyCard,
  useStudySound,
  type Milestone,
} from "./experience";
import { hasPythonBackend, openDocument } from "./backend";
import "./style.css";
import "./earl-gray.css";

type Review = { ids: string[]; index: number };
function rememberedDeck() {
  try {
    return localStorage.getItem("note-that-active") || demoDeck.id;
  } catch {
    return demoDeck.id;
  }
}

type Modal =
  "import" | "help" | "sections" | "revisit" | "reset" | "sound" | null;
function Bolt({ small = false }: { small?: boolean }) {
  return (
    <svg
      className={small ? "bolt small" : "bolt"}
      viewBox="0 0 30 38"
      fill="none"
      aria-label="red lightning"
    >
      <path
        d="M17.5 1.5 2.5 22h11l-2 14.5L28 14H17l.5-12.5Z"
        fill="currentColor"
      />
    </svg>
  );
}
function Spotlight({ art = "spotlight" }: { art?: Slide["art"] }) {
  if (art === "memory")
    return (
      <svg
        className="slide-art"
        viewBox="0 0 290 270"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M37 185c26-104 64-116 89-63 30 64 39 72 55 10 13-53 37-60 68 0"
          stroke="#73806a"
          strokeWidth="2"
          strokeDasharray="4 5"
        />
        <ellipse cx="146" cy="207" rx="111" ry="17" fill="#ebe8dc" />
        <rect
          x="58"
          y="97"
          width="108"
          height="129"
          rx="5"
          transform="rotate(-14 58 97)"
          fill="#e3dfcc"
          stroke="#aea990"
        />
        <rect
          x="96"
          y="70"
          width="108"
          height="139"
          rx="5"
          transform="rotate(7 96 70)"
          fill="#f6f3e7"
          stroke="#9e9d87"
        />
        <path
          d="m122 111 50 6m-53 16 64 8m-67 16 55 7"
          stroke="#b5b19c"
          strokeWidth="2"
        />
        <path
          d="m133 178 9 10 22-23"
          stroke="#798669"
          strokeWidth="3"
          strokeLinecap="round"
        />
        <path
          d="m218 49 3 10 10 3-10 3-3 10-3-10-10-3 10-3 3-10Z"
          fill="#ba6c53"
        />
        <circle cx="58" cy="61" r="4" fill="#ba6c53" />
      </svg>
    );
  if (art === "focus")
    return (
      <svg
        className="slide-art"
        viewBox="0 0 290 270"
        fill="none"
        aria-hidden="true"
      >
        <circle
          cx="148"
          cy="135"
          r="99"
          stroke="#d5d1bf"
          strokeDasharray="3 7"
        />
        <circle cx="148" cy="135" r="69" fill="#eeeadd" stroke="#c8c3ac" />
        <circle cx="148" cy="135" r="36" fill="#d8ddc9" stroke="#8b9677" />
        <circle cx="148" cy="135" r="7" fill="#788460" />
        <path
          d="m216 54-64 73m52-73 12 0 0 13"
          stroke="#b9694f"
          strokeWidth="2"
          strokeLinecap="round"
        />
        <path d="m63 78 3 8 8 3-8 3-3 8-3-8-8-3 8-3 3-8Z" fill="#b9694f" />
        <circle cx="236" cy="194" r="4" fill="#a3ac8c" />
        <path d="m63 201 5 5m-5 0 5-5" stroke="#a9a58f" />
      </svg>
    );
  return (
    <svg
      className="slide-art"
      viewBox="0 0 290 270"
      fill="none"
      aria-hidden="true"
    >
      <defs>
        <linearGradient
          id="beam"
          x1="155"
          y1="71"
          x2="155"
          y2="233"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#d6ddc5" stopOpacity=".2" />
          <stop offset="1" stopColor="#d6ddc5" stopOpacity=".9" />
        </linearGradient>
      </defs>
      <path d="m143 78-80 144h179L169 78" fill="url(#beam)" />
      <ellipse cx="152" cy="224" rx="90" ry="17" fill="#d8dfc8" />
      <ellipse
        cx="152"
        cy="224"
        rx="59"
        ry="10"
        stroke="#b9c6a5"
        strokeDasharray="3 4"
      />
      <path d="m177 34-36 38" stroke="#6e765f" strokeWidth="2" />
      <path d="m146 56 21 14 5 21c-14 5-28 2-38-8l12-27Z" fill="#788264" />
      <ellipse
        cx="153"
        cy="84"
        rx="20"
        ry="7"
        transform="rotate(20 153 84)"
        fill="#b1bc96"
        stroke="#6f795f"
      />
      <path
        d="m146 196 5 13 14 1-11 9 3 14-12-8-12 7 4-14-10-9 14-1 5-12Z"
        fill="#b96d53"
      />
      <path d="m90 139 3 8 9 3-9 3-3 8-3-8-8-3 8-3 3-8Z" fill="#858e71" />
      <path d="m220 86 3 9 9 3-9 3-3 9-3-9-9-3 9-3 3-9Z" stroke="#bdb8a3" />
      <path d="m55 195 3 7 7 2-7 3-3 7-2-7-7-3 7-2 2-7Z" stroke="#bdb8a3" />
      <circle cx="207" cy="166" r="3" fill="#929d7c" />
      <circle cx="73" cy="78" r="3" fill="#c2bca6" />
      <path d="m191 137 4 4m-4 0 4-4" stroke="#aab397" />
      <path d="m111 40 4 4m-4 0 4-4" stroke="#b9af96" />
    </svg>
  );
}
function App() {
  const [decks, setDecks] = useState<Deck[]>([structuredClone(demoDeck)]);
  const [selected, setSelected] = useState(rememberedDeck);
  const [loaded, setLoaded] = useState(false);
  const [view, setView] = useState<"study" | "library" | "progress">("study");
  const [modal, setModal] = useState<Modal>(null);
  const [checkpoint, setCheckpoint] = useState<number | null>(null);
  const [review, setReview] = useState<Review | null>(null);
  const [history, setHistory] = useState<
    { deck: Deck; checkpoint: number | null; review: Review | null }[]
  >([]);
  const [toast, setToast] = useState("");
  const [saveState, setSaveState] = useState<"saved" | "saving" | "error">(
    "saved",
  );
  const [query, setQuery] = useState("");
  const [importMessage, setImportMessage] = useState("");
  const [importError, setImportError] = useState("");
  const [dragOver, setDragOver] = useState(false);
  const [fly, setFly] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const [sectionEdits, setSectionEdits] = useState<
    { title: string; start: number }[]
  >([]);
  const [sectionError, setSectionError] = useState("");
  const fileInput = useRef<HTMLInputElement>(null);
  const swipeDirection = useRef(1);
  const swipeLock = useRef(false);
  const sound = useStudySound();
  const reducedMotion = useReducedMotion();
  const [dark, setDark] = useState(() => {
    try {
      return localStorage.getItem("note-that-theme") === "dark";
    } catch {
      return false;
    }
  });
  useEffect(() => {
    document.documentElement.dataset.theme = dark ? "dark" : "light";
    try {
      localStorage.setItem("note-that-theme", dark ? "dark" : "light");
    } catch {
      /* Theme works for this session. */
    }
  }, [dark]);
  const [pythonMode, setPythonMode] = useState(false);
  const [milestone, setMilestone] = useState<Milestone | null>(null);
  const finishCelebration = useCallback(() => setMilestone(null), []);
  const readyCard = useCallback(() => {
    swipeLock.current = false;
    setFly(0);
  }, []);
  useEffect(() => {
    void hasPythonBackend().then(setPythonMode);
  }, []);
  const modalRef = useRef<HTMLDivElement>(null);
  const saveChain = useRef(Promise.resolve());
  const [expanded, setExpanded] = useState(false);
  const deck = decks.find((d) => d.id === selected) || decks[0];
  const firstIncomplete = nextSection(deck);
  const sectionIndex =
    checkpoint ??
    (firstIncomplete < 0 ? deck.sections.length - 1 : firstIncomplete);
  const section = deck.sections[sectionIndex];
  const undecided = deck.slides
    .slice(section.start, section.end + 1)
    .find((s) => !deck.decisions[s.id]);
  const slide = review
    ? deck.slides.find((s) => s.id === review.ids[review.index])
    : undecided;
  const slideIndex = slide
    ? deck.slides.findIndex((s) => s.id === slide.id)
    : -1;
  const confident = Object.values(deck.decisions).filter(
    (d) => d === "confident",
  ).length;
  const saved = deck.slides.filter((s) => deck.decisions[s.id] === "revisit");
  const completed = Object.keys(deck.decisions).length;
  const percent = Math.round((completed / deck.slides.length) * 100);
  const sectionSaved = saved.filter(
    (s) =>
      deck.slides.indexOf(s) >= section.start &&
      deck.slides.indexOf(s) <= section.end,
  );
  const isDone = !review && firstIncomplete < 0 && checkpoint === null;
  useEffect(() => {
    let cancelled = false;
    loadDecks()
      .then((items) => {
        if (cancelled) return;
        if (items.length)
          setDecks(
            items.some((d) => d.id === demoDeck.id)
              ? items
              : [structuredClone(demoDeck), ...items],
          );
        setLoaded(true);
      })
      .catch(() => {
        if (!cancelled) {
          setSaveState("error");
          setLoaded(true);
          setToast(
            "Browser storage is unavailable. Progress will last for this session only.",
          );
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);
  useEffect(() => {
    const timer = window.setInterval(() => {
      if (
        document.visibilityState === "visible" &&
        view === "study" &&
        !modal &&
        slide
      )
        setElapsed((n) => n + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [view, modal, !!slide]);
  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(""), 5000);
    return () => clearTimeout(timer);
  }, [toast]);
  useEffect(() => {
    if (!modal && !expanded) return;
    const previous = document.activeElement as HTMLElement;
    const timer = setTimeout(
      () =>
        modalRef.current?.querySelector<HTMLElement>("button, input")?.focus(),
      0,
    );
    function trap(event: KeyboardEvent) {
      if (event.key === "Escape" && !importMessage) {
        setModal(null);
        setExpanded(false);
      }
      if (event.key === "Tab") {
        const nodes = modalRef.current?.querySelectorAll<HTMLElement>(
          'button:not(:disabled), input:not(:disabled), [tabindex="0"]',
        );
        if (!nodes?.length) return;
        const first = nodes[0],
          last = nodes[nodes.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", trap);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("keydown", trap);
      previous?.focus();
    };
  }, [modal, expanded, importMessage]);
  function updateDeck(updated: Deck) {
    setDecks((all) => all.map((d) => (d.id === updated.id ? updated : d)));
    setSaveState("saving");
    saveChain.current = saveChain.current
      .catch(() => {})
      .then(() => saveDeck(updated))
      .then(() => setSaveState("saved"))
      .catch(() => {
        setSaveState("error");
        setToast(
          "Your browser couldn’t save this change. Please check available storage.",
        );
      });
  }
  function selectDeck(id: string) {
    readyCard();
    setMilestone(null);
    setSelected(id);
    try {
      localStorage.setItem("note-that-active", id);
    } catch {
      /* IndexedDB remains the source of progress. */
    }
    setCheckpoint(null);
    setReview(null);
    setHistory([]);
    setView("study");
  }
  function decide(direction: Decision) {
    if (!slide || swipeLock.current || modal || !loaded || expanded) return;
    swipeLock.current = true;
    swipeDirection.current = direction === "confident" ? -1 : 1;
    setFly(swipeDirection.current);
    const previous = {
      deck: structuredClone(deck),
      checkpoint,
      review: review ? { ...review } : null,
    };
    setHistory((h) => [...h.slice(-49), previous]);
    const updated = {
      ...deck,
      decisions: { ...deck.decisions, [slide.id]: direction },
      revisited:
        review && !deck.revisited.includes(slide.id)
          ? [...deck.revisited, slide.id]
          : deck.revisited,
    };
    updateDeck(updated);
    if (review) {
      sound.play(direction);
      setReview({ ...review, index: review.index + 1 });
    } else if (sectionDone(updated, section)) {
      setCheckpoint(sectionIndex);
      const kind = nextSection(updated) < 0 ? "document" : "section";
      setMilestone({ id: performance.now(), kind });
      sound.play(kind);
    } else sound.play(direction);
  }
  function undo() {
    if (!history.length) return;
    readyCard();
    setMilestone(null);
    swipeDirection.current *= -1;
    const last = history[history.length - 1];
    updateDeck(last.deck);
    setCheckpoint(last.checkpoint);
    setReview(last.review);
    setHistory((h) => h.slice(0, -1));
    setToast("Last swipe undone. A fresh look.");
  }
  useEffect(() => {
    function key(event: KeyboardEvent) {
      if (
        modal ||
        view !== "study" ||
        expanded ||
        ["INPUT", "TEXTAREA", "SELECT"].includes(
          (event.target as HTMLElement).tagName,
        )
      )
        return;
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        decide("confident");
      } else if (event.key === "ArrowRight") {
        event.preventDefault();
        decide("revisit");
      } else if (
        event.key.toLowerCase() === "z" &&
        !event.metaKey &&
        !event.ctrlKey
      )
        undo();
    }
    window.addEventListener("keydown", key);
    return () => window.removeEventListener("keydown", key);
  });
  async function handleFile(file?: File) {
    if (!file || importMessage) return;
    setImportError("");
    setImportMessage("Opening your document…");
    try {
      const imported = await openDocument(file, setImportMessage);
      await saveDeck(imported);
      setDecks((all) => [...all, imported]);
      selectDeck(imported.id);
      setModal(null);
      setToast(
        imported.kind === "pptx"
          ? "Your slides are ready in text view. Import a PDF to preserve their original design."
          : "Your document is ready. Make yourself at home.",
      );
    } catch (error) {
      const message =
        error instanceof Error
          ? error.message
          : "Could not open that document.";
      setImportError(
        /password/i.test(message)
          ? "This PDF is password protected. Please upload an unlocked copy."
          : message,
      );
    } finally {
      setImportMessage("");
      if (fileInput.current) fileInput.current.value = "";
    }
  }
  function startReview(ids: string[]) {
    if (!ids.length) return;
    setReview({ ids, index: 0 });
    setModal(null);
    setView("study");
    setHistory([]);
  }
  function openSections() {
    setSectionEdits(
      deck.sections.map((s) => ({ title: s.title, start: s.start + 1 })),
    );
    setSectionError("");
    setModal("sections");
  }
  function saveSections() {
    const items = sectionEdits;
    if (
      !items.length ||
      items[0].start !== 1 ||
      items.some(
        (s, i) =>
          !s.title.trim() ||
          !Number.isInteger(s.start) ||
          s.start < 1 ||
          s.start > deck.slides.length ||
          (i > 0 && s.start <= items[i - 1].start),
      )
    ) {
      setSectionError(
        "Start at page 1, give each section a name, and use increasing page numbers.",
      );
      return;
    }
    updateDeck({
      ...deck,
      sections: items.map((s, i) => ({
        id: `section-${i}`,
        title: s.title.trim(),
        start: s.start - 1,
        end: (items[i + 1]?.start ?? deck.slides.length + 1) - 2,
      })),
    });
    setCheckpoint(null);
    setReview(null);
    setHistory([]);
    setModal(null);
    setToast("Your study path has been updated.");
  }
  const renderSlide = (large = false) =>
    slide &&
    (slide.image ? (
      <div className={`image-slide ${large ? "large" : ""}`}>
        <img
          src={slide.image}
          alt={`${deck.title}, page ${slide.page}: ${slide.title}`}
          draggable="false"
        />
      </div>
    ) : (
      <div
        className={`editorial-slide ${deck.kind === "pptx" ? "text-slide" : slideIndex === 0 ? "intro-slide" : "lesson-slide"}`}
      >
        <div className="slide-topline">
          <span>
            {deck.kind === "demo" ? "A FIELD GUIDE TO YOUR MIND" : deck.title}
          </span>
          <span>{String(slide.page).padStart(2, "0")}</span>
        </div>
        <div className="slide-inner">
          <div className="slide-copy">
            <span className="slide-eyebrow">
              {slideIndex === 0
                ? "LET’S START WITH THE BASICS"
                : slide.kicker || "TAKE A MOMENT. TAKE IT IN."}
            </span>
            <h2>{slide.title}</h2>
            <p>{slide.body}</p>
            {slideIndex === 0 && <span className="drawn-line" />}
          </div>
          {deck.kind === "demo" && <Spotlight art={slide.art} />}
        </div>
        <div className="slide-bottomline">
          <span>
            {slideIndex === 0
              ? slide.kicker
              : "A little more familiar, one slide at a time."}
          </span>
          <span>
            note that <Bolt small />
          </span>
        </div>
      </div>
    ));
  return (
    <div className="app-shell">
      <header className="site-header">
        <button
          className="wordmark"
          onClick={() => setView("study")}
          aria-label="note that home"
        >
          <Bolt />
          <span>
            note that<span className="wordmark-period">.</span>
          </span>
        </button>
        <span className="sidebar-tagline">A LITTLE MORE FAMILIAR.</span>
        <button
          className="sidebar-import-button"
          onClick={() => {
            setImportError("");
            setModal("import");
          }}
        >
          <Plus size={19} /> Add files
        </button>
        <nav aria-label="Main navigation">
          {(["study", "library", "progress"] as const).map((item) => (
            <button
              key={item}
              className={view === item ? "nav-item active" : "nav-item"}
              onClick={() => setView(item)}
            >
              {item === "study" ? (
                <Layers3 size={17} />
              ) : item === "library" ? (
                <FolderOpen size={17} />
              ) : (
                <Sparkles size={17} />
              )}
              {item === "study"
                ? "Study space"
                : item === "library"
                  ? "My library"
                  : "Your progress"}
              {item === "study" && <span className="nav-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-guide">
          <span>THREE LITTLE STEPS</span>
          <p>
            <i>1</i> Bring your slides
          </p>
          <p>
            <i>2</i> Swipe and learn
          </p>
          <p>
            <i>3</i> Come back stronger
          </p>
        </div>
        <div className="sidebar-privacy">
          <ShieldCheck size={20} />
          <strong>Your space to learn.</strong>
          <span>
            No accounts. Just you
            <br />
            and your next little win.
          </span>
        </div>
        <div className="header-right">
          <button
            className="theme-button"
            onClick={() => setDark(!dark)}
            aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
            title={dark ? "Light mode" : "Dark mode"}
          >
            {dark ? <Moon size={17} /> : <Sun size={17} />}
          </button>
          <button
            className={`sound-button ${sound.enabled ? "enabled" : ""}`}
            onClick={() => setModal("sound")}
            aria-label="Sound settings"
            title="Sound settings"
          >
            {sound.enabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
            <span className="sound-label">
              Sound {sound.enabled ? "on" : "off"}
            </span>
          </button>
          <button className="shortcut-button" onClick={() => setModal("help")}>
            <Keyboard size={17} />
            <span>A little help</span>
          </button>
          <span className="header-divider" />
          <button
            className="avatar"
            onClick={() => setView("progress")}
            aria-label="Your study progress"
          >
            you
            <span />
          </button>
        </div>
      </header>
      <main>
        <section className="page-heading">
          <div>
            <div className="eyebrow">
              <span className="tiny-sun">✳</span> A LITTLE FOCUS GOES A LONG WAY
            </div>
            <h1>
              {view === "study" ? (
                <>
                  Your slides, <em>a little clearer.</em>
                </>
              ) : view === "library" ? (
                <>
                  Your little <em>library.</em>
                </>
              ) : (
                <>
                  Look at you <em>grow.</em>
                </>
              )}
            </h1>
            <p>
              {view === "study"
                ? "Less cramming. More understanding. One slide at a time."
                : view === "library"
                  ? "Good ideas, all in one place. Pick up where you left off."
                  : "Small sessions add up. Here’s what you’re making familiar."}
            </p>
          </div>
          <button
            className="import-button"
            onClick={() => {
              setImportError("");
              setModal("import");
            }}
          >
            <Plus size={18} />
            <span>Import a document</span>
            <span className="file-types">PDF / PPTX</span>
          </button>
        </section>
        {view === "study" && (
          <div className="focus-banner">
            <Layers3 size={24} />
            <div>
              <strong>Little swipes. Lasting knowledge.</strong>
              <p>Left when you know it. Right for a second look.</p>
            </div>
            <Bolt />
          </div>
        )}
        {view === "study" ? (
          <>
            <div className="document-bar">
              <button
                className="document-selector"
                onClick={() => setView("library")}
              >
                <span className="doc-icon">
                  <FileText size={20} />
                </span>
                <span>
                  <strong>{deck.title}</strong>
                  <span className="document-meta">
                    {deck.slides.length} slides <i>·</i> {deck.sections.length}{" "}
                    sections{deck.kind === "pptx" && " · Text view"}
                  </span>
                </span>
                <ChevronDown size={16} />
              </button>
              {deck.kind === "demo" && (
                <span className="demo-badge">A little demo</span>
              )}
              <span className={`save-status ${saveState}`}>
                <span />
                {saveState === "saved"
                  ? "Your progress is saved"
                  : saveState === "saving"
                    ? "Saving your progress…"
                    : "Progress not saved"}
              </span>
            </div>
            <div className="workspace-grid">
              <section className="study-column" aria-label="Slide study space">
                <div className="study-section-bar">
                  <span className="section-caption">
                    {review ? (
                      <>
                        <Bookmark size={13} /> YOUR SECOND LOOK
                      </>
                    ) : (
                      <>
                        <span>{String(sectionIndex + 1).padStart(2, "0")}</span>
                        <span className="caption-slash">/</span>
                        {section.title.toUpperCase()}
                      </>
                    )}
                  </span>
                  <span className="slide-count">
                    {review
                      ? `${Math.min(review.index + 1, review.ids.length)} of ${review.ids.length} to revisit`
                      : `${slideIndex >= 0 ? slideIndex - section.start + 1 : section.end - section.start + 1} / ${section.end - section.start + 1} slides`}
                    <span className="mini-dots">
                      {Array.from(
                        {
                          length: Math.min(
                            review
                              ? review.ids.length
                              : section.end - section.start + 1,
                            8,
                          ),
                        },
                        (_, i) => (
                          <i
                            key={i}
                            className={
                              (
                                review
                                  ? i < review.index
                                  : !!deck.decisions[
                                      deck.slides[section.start + i]?.id
                                    ]
                              )
                                ? "done"
                                : i ===
                                    (review
                                      ? review.index
                                      : slideIndex - section.start)
                                  ? "current"
                                  : ""
                            }
                          />
                        ),
                      )}
                    </span>
                  </span>
                </div>
                <div className={`card-stage ${fly ? "flying" : ""}`}>
                  <AnimatePresence
                    mode="wait"
                    initial={false}
                    custom={swipeDirection.current}
                  >
                    {slide ? (
                      <JellyCard
                        key={`${deck.id}-${slide.id}`}
                        image={!!slide.image}
                        onDecision={decide}
                        onReady={readyCard}
                        disabled={!!fly || !loaded || !!modal || expanded}
                      >
                        {renderSlide()}
                        {slide.image && (
                          <button
                            className="expand-button"
                            title="Enlarge slide"
                            aria-label="Enlarge slide"
                            onPointerDown={(e) => e.stopPropagation()}
                            onClick={() => setExpanded(true)}
                          >
                            <ArrowUpRight size={18} />
                          </button>
                        )}
                      </JellyCard>
                    ) : (
                      <motion.div
                        key={`completion-${deck.id}-${checkpoint}-${review ? "review" : "study"}`}
                        className="study-card completion-card"
                        initial={{
                          opacity: 0,
                          scale: reducedMotion ? 1 : 0.96,
                        }}
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0 }}
                        transition={{
                          type: "spring",
                          stiffness: 240,
                          damping: 20,
                        }}
                        onAnimationComplete={readyCard}
                      >
                        <span className="completion-icon">
                          {isDone ? (
                            <Sparkles size={34} />
                          ) : (
                            <CheckCheck size={34} />
                          )}
                        </span>
                        <div className="eyebrow">
                          {review
                            ? "A LITTLE MORE FAMILIAR"
                            : isDone
                              ? "LOOK HOW FAR YOU’VE COME"
                              : "ONE SMALL WIN, RIGHT THERE"}
                        </div>
                        <h2>
                          {review
                            ? "That’s your second look."
                            : isDone
                              ? "You made it through."
                              : "Section, sorted."}
                        </h2>
                        <p>
                          {review
                            ? "Every second look is a step toward understanding."
                            : isDone
                              ? `All ${deck.slides.length} slides, one thoughtful moment at a time.`
                              : `You’ve seen every slide in ${section.title.toLowerCase()}. Let it settle for a moment.`}
                        </p>
                        <div className="completion-actions">
                          {review ? (
                            <button
                              className="primary-button"
                              onClick={() => {
                                setReview(null);
                                setHistory([]);
                              }}
                            >
                              Back to my study path <ArrowRight size={16} />
                            </button>
                          ) : (
                            <>
                              {(checkpoint !== null ? sectionSaved : saved)
                                .length > 0 && (
                                <button
                                  className="primary-button"
                                  onClick={() =>
                                    startReview(
                                      (checkpoint !== null
                                        ? sectionSaved
                                        : saved
                                      ).map((s) => s.id),
                                    )
                                  }
                                >
                                  <Bookmark size={16} /> Revisit{" "}
                                  {checkpoint !== null
                                    ? sectionSaved.length
                                    : saved.length}{" "}
                                  saved slides
                                </button>
                              )}
                              {checkpoint !== null && (
                                <button
                                  className={
                                    sectionSaved.length
                                      ? "text-button"
                                      : "primary-button"
                                  }
                                  onClick={() => {
                                    setCheckpoint(null);
                                    setHistory([]);
                                  }}
                                >
                                  {sectionIndex < deck.sections.length - 1
                                    ? "On to the next section"
                                    : "Finish this session"}
                                  <ArrowRight size={16} />
                                </button>
                              )}
                              {isDone && (
                                <button
                                  className="text-button"
                                  onClick={() => setView("library")}
                                >
                                  Find something else to study{" "}
                                  <ArrowRight size={16} />
                                </button>
                              )}
                            </>
                          )}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
                <div className="swipe-controls">
                  <button
                    className="undo-button"
                    onClick={undo}
                    disabled={!history.length || !!fly}
                    title="Undo last swipe (Z)"
                    aria-label="Undo last swipe"
                  >
                    <RotateCcw size={18} />
                  </button>
                  <button
                    className="decision-button know-button"
                    onClick={() => decide("confident")}
                    disabled={!slide || !!fly || !loaded}
                  >
                    <span className="key-cap">←</span>
                    <Check size={19} />
                    <span>I know this</span>
                  </button>
                  <button
                    className="decision-button later-button"
                    onClick={() => decide("revisit")}
                    disabled={!slide || !!fly || !loaded}
                  >
                    <Bookmark size={17} />
                    <span>Revisit later</span>
                    <span className="key-cap">→</span>
                  </button>
                  <button
                    className="more-button"
                    onClick={() => setModal("reset")}
                    title="Restart this document"
                    aria-label="Restart this document"
                  >
                    <MoreHorizontal size={21} />
                  </button>
                </div>
                <div className="swipe-hint">
                  <span className="hint-line" />
                  <span>
                    Swipe the card, or let your arrow keys do the work.
                  </span>
                  <span className="hint-line" />
                </div>
                <div className="revisit-strip">
                  <span className="revisit-icon">
                    <Bookmark size={19} />
                  </span>
                  <div>
                    <strong>
                      Your revisit pile <span>{saved.length}</span>
                    </strong>
                    <p>
                      {saved.length
                        ? `${saved.length} ${saved.length === 1 ? "slide is" : "slides are"} waiting for a fresh pair of eyes.`
                        : "The tricky ones get a second chance. Save them here."}
                    </p>
                  </div>
                  <button
                    className="text-button"
                    onClick={() => setModal("revisit")}
                  >
                    Take a look <ArrowUpRight size={15} />
                  </button>
                </div>
              </section>
              <aside className="study-sidebar">
                <div className="sidebar-title">
                  <h2>Your study path</h2>
                  <button
                    className="icon-button"
                    onClick={openSections}
                    aria-label="Edit sections"
                    title="Edit sections"
                  >
                    <Settings2 size={16} />
                  </button>
                </div>
                <p className="sidebar-subtitle">
                  Small sections. Steady progress.
                </p>
                <div className="section-list">
                  {deck.sections.map((s, i) => {
                    const done = sectionDone(deck, s);
                    const locked = firstIncomplete >= 0 && i > firstIncomplete;
                    const active = !review && i === sectionIndex;
                    const count = deck.slides
                      .slice(s.start, s.end + 1)
                      .filter((sl) => deck.decisions[sl.id]).length;
                    return (
                      <button
                        key={s.id}
                        className={`path-item ${active ? "active" : ""} ${done ? "completed" : ""} ${locked ? "locked" : ""}`}
                        disabled={locked}
                        onClick={() => {
                          if (done)
                            startReview(
                              deck.slides
                                .slice(s.start, s.end + 1)
                                .map((s) => s.id),
                            );
                          else {
                            setReview(null);
                            setCheckpoint(null);
                          }
                        }}
                      >
                        <span className="path-number">
                          {done ? (
                            <Check size={15} />
                          ) : (
                            String(i + 1).padStart(2, "0")
                          )}
                        </span>
                        <span className="path-copy">
                          <strong>{s.title}</strong>
                          <small>
                            {s.end - s.start + 1} slides <i>·</i>{" "}
                            {done
                              ? "Complete"
                              : active
                                ? "You are here"
                                : "Up next"}
                          </small>
                          {active && (
                            <span className="path-progress">
                              <i
                                style={{
                                  width: `${(count / (s.end - s.start + 1)) * 100}%`,
                                }}
                              />
                            </span>
                          )}
                        </span>
                        {locked ? (
                          <LockKeyhole size={13} />
                        ) : active ? (
                          <span className="active-path-dot" />
                        ) : (
                          <ChevronRight size={14} />
                        )}
                      </button>
                    );
                  })}
                </div>
                <div className="path-footnote">
                  <LockKeyhole size={12} />
                  <span>Finish a section to unlock the next.</span>
                </div>
                <div className="gentle-reminder">
                  <div>
                    <Sparkles size={16} />
                    <span>A LITTLE REMINDER</span>
                  </div>
                  <p>
                    You don’t have to know it all.
                    <br />
                    You just have to <em>come back.</em>
                  </p>
                  <span>That’s where the learning happens.</span>
                  <svg viewBox="0 0 66 40" aria-hidden="true">
                    <path
                      d="M2 34c16 1 15-26 31-21 18 5-13 26-7 13L43 6m-9 1 10-3-1 11"
                      stroke="currentColor"
                      strokeWidth="1.5"
                      fill="none"
                      strokeLinecap="round"
                    />
                  </svg>
                </div>
                <div className="session-card">
                  <div className="session-card-title">
                    <span>YOUR DOCUMENT</span>
                    <Clock3 size={13} />
                  </div>
                  <div className="session-numbers">
                    <div>
                      <strong>
                        {confident}
                        <span className="stat-dot green" />
                      </strong>
                      <span>Feeling confident</span>
                    </div>
                    <span className="stat-divider" />
                    <div>
                      <strong>
                        {saved.length}
                        <span className="stat-dot red" />
                      </strong>
                      <span>To revisit</span>
                    </div>
                  </div>
                  <div className="overall-progress">
                    <span>
                      <b>{percent}%</b> of the way there
                    </span>
                    <span>{Math.floor(elapsed / 60)} min focused</span>
                  </div>
                  <div className="progress-track">
                    <span style={{ width: `${percent}%` }} />
                  </div>
                </div>
              </aside>
            </div>
          </>
        ) : view === "library" ? (
          <section className="library-page">
            <div className="library-toolbar">
              <h2>
                A shelf for your thoughts <span>{decks.length}</span>
              </h2>
              <label className="search-box">
                <Search size={16} />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Find a document…"
                  aria-label="Find a document"
                />
              </label>
            </div>
            <div className="library-grid">
              {decks
                .filter((d) =>
                  d.title.toLowerCase().includes(query.toLowerCase()),
                )
                .map((d, i) => (
                  <article className="deck-tile" key={d.id}>
                    <button
                      className={`deck-cover cover-${i % 3}`}
                      onClick={() => selectDeck(d.id)}
                    >
                      <span className="cover-top">
                        {d.kind === "demo"
                          ? "A FIELD GUIDE TO YOUR MIND"
                          : d.kind.toUpperCase() + " · YOUR PERSONAL LIBRARY"}
                      </span>
                      {d.slides[0]?.image ? (
                        <img src={d.slides[0].image} alt="First page preview" />
                      ) : (
                        <>
                          <h3>{d.title}</h3>
                          <Spotlight art={i % 2 ? "memory" : "spotlight"} />
                        </>
                      )}
                      <span className="cover-bottom">
                        {d.slides.length} slides <ArrowUpRight size={19} />
                      </span>
                    </button>
                    <div className="deck-details">
                      <div>
                        <h3>{d.title}</h3>
                        <p>
                          {d.sections.length} sections ·{" "}
                          {Math.round(
                            (Object.keys(d.decisions).length /
                              d.slides.length) *
                              100,
                          )}
                          % explored
                        </p>
                      </div>
                      {d.kind !== "demo" && (
                        <button
                          className="icon-button"
                          aria-label={`Delete ${d.title}`}
                          onClick={async () => {
                            if (
                              !window.confirm(
                                `Remove “${d.title}” and its study progress from this browser?`,
                              )
                            )
                              return;
                            try {
                              await deleteDeck(d.id);
                              setDecks((all) =>
                                all.filter((x) => x.id !== d.id),
                              );
                              if (selected === d.id) selectDeck(demoDeck.id);
                              setToast("Document removed from your library.");
                            } catch {
                              setToast(
                                "Could not remove this document. Please try again.",
                              );
                            }
                          }}
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                    </div>
                    <button
                      className="tile-study-button"
                      onClick={() => selectDeck(d.id)}
                    >
                      {Object.keys(d.decisions).length
                        ? "Pick up where you left off"
                        : "Make a little start"}{" "}
                      <ArrowRight size={15} />
                    </button>
                  </article>
                ))}
              <button className="new-deck" onClick={() => setModal("import")}>
                <span>
                  <Plus size={27} />
                </span>
                <strong>Room for something new.</strong>
                <p>Bring your slides. We’ll bring the focus.</p>
                <small>PDF, PowerPoint, or images</small>
              </button>
            </div>
            {query &&
              !decks.some((d) =>
                d.title.toLowerCase().includes(query.toLowerCase()),
              ) && (
                <p className="empty-search">
                  No documents match “{query}”. A new import, perhaps?
                </p>
              )}
          </section>
        ) : (
          <section className="progress-page">
            <div className="big-stats">
              {[
                {
                  icon: <Layers3 />,
                  value: decks.reduce(
                    (n, d) => n + Object.keys(d.decisions).length,
                    0,
                  ),
                  label: "Slides explored",
                  desc: "One at a time. Just like that.",
                },
                {
                  icon: <CheckCheck />,
                  value: decks.reduce(
                    (n, d) =>
                      n +
                      Object.values(d.decisions).filter(
                        (x) => x === "confident",
                      ).length,
                    0,
                  ),
                  label: "Feeling confident",
                  desc: "Ideas that feel a little more familiar.",
                },
                {
                  icon: <Bookmark />,
                  value: decks.reduce(
                    (n, d) =>
                      n +
                      Object.values(d.decisions).filter((x) => x === "revisit")
                        .length,
                    0,
                  ),
                  label: "Worth another look",
                  desc: "Your next opportunity to learn.",
                },
              ].map((stat) => (
                <div className="big-stat" key={stat.label}>
                  <span className="big-stat-icon">{stat.icon}</span>
                  <strong>{stat.value}</strong>
                  <h3>{stat.label}</h3>
                  <p>{stat.desc}</p>
                </div>
              ))}
            </div>
            <div className="progress-decks">
              <h2>A little progress, everywhere.</h2>
              {decks.map((d) => (
                <button key={d.id} onClick={() => selectDeck(d.id)}>
                  <span className="doc-icon">
                    <FileText size={20} />
                  </span>
                  <span className="progress-deck-name">
                    <strong>{d.title}</strong>
                    <small>
                      {Object.keys(d.decisions).length} of {d.slides.length}{" "}
                      slides explored
                    </small>
                  </span>
                  <span className="progress-track">
                    <span
                      style={{
                        width: `${(Object.keys(d.decisions).length / d.slides.length) * 100}%`,
                      }}
                    />
                  </span>
                  <span className="progress-percent">
                    {Math.round(
                      (Object.keys(d.decisions).length / d.slides.length) * 100,
                    )}
                    %
                  </span>
                  <ArrowUpRight size={17} />
                </button>
              ))}
            </div>
            <p className="progress-note">
              <Sparkles size={16} /> You’re not racing anyone. This is your
              pace.
            </p>
          </section>
        )}
        <footer className="site-footer">
          <span>
            <Bolt small /> A little more familiar, every day.
          </span>
          <span>
            Made for your <em>aha</em> moments.
            <span className="footer-star">✳</span>
          </span>
        </footer>
      </main>
      {(modal || expanded) && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget && !importMessage) {
              setModal(null);
              setExpanded(false);
            }
          }}
        >
          <div
            className={`modal ${expanded ? "expanded-modal" : ""}`}
            ref={modalRef}
            role="dialog"
            aria-modal="true"
            aria-label={
              expanded
                ? "Slide enlarged"
                : modal === "import"
                  ? "Import a document"
                  : modal === "help"
                    ? "A little help"
                    : modal === "sections"
                      ? "Edit sections"
                      : modal === "reset"
                        ? "Restart document"
                        : modal === "sound"
                          ? "Sound settings"
                          : "Your revisit pile"
            }
          >
            <button
              className="modal-close icon-button"
              aria-label="Close dialog"
              disabled={!!importMessage}
              onClick={() => {
                setModal(null);
                setExpanded(false);
              }}
            >
              <X size={21} />
            </button>
            {expanded ? (
              renderSlide(true)
            ) : modal === "import" ? (
              <>
                <span className="modal-symbol">
                  <Upload size={24} />
                </span>
                <div className="eyebrow">A NEW CHAPTER STARTS HERE</div>
                <h2>Bring your ideas.</h2>
                <p>Your slides, your pace. Let’s make them stick.</p>
                <input
                  ref={fileInput}
                  type="file"
                  accept=".pdf,.pptx,.png,.jpg,.jpeg,.webp"
                  className="sr-only"
                  aria-label="Choose a document"
                  disabled={!!importMessage}
                  onChange={(e) => handleFile(e.target.files?.[0])}
                />
                <button
                  className={`drop-zone ${dragOver ? "drag-over" : ""}`}
                  disabled={!!importMessage}
                  onClick={() => fileInput.current?.click()}
                  onDragOver={(e) => {
                    e.preventDefault();
                    setDragOver(true);
                  }}
                  onDragLeave={() => setDragOver(false)}
                  onDrop={(e) => {
                    e.preventDefault();
                    setDragOver(false);
                    handleFile(e.dataTransfer.files[0]);
                  }}
                >
                  <span
                    className={
                      importMessage ? "upload-icon spinning" : "upload-icon"
                    }
                  >
                    {importMessage ? (
                      <RotateCcw size={27} />
                    ) : (
                      <FolderOpen size={29} />
                    )}
                  </span>
                  <strong>{importMessage || "Drop a document here"}</strong>
                  <span>
                    {importMessage ? (
                      "A little preparation for a lot of learning."
                    ) : (
                      <>
                        or <u>browse your files</u>
                      </>
                    )}
                  </span>
                  <small>PDF, PPTX, PNG, JPG, WEBP · Up to 100 MB</small>
                </button>
                {importError && (
                  <div className="error-message" role="alert">
                    {importError}
                  </div>
                )}
                <div className="import-note">
                  <LockKeyhole size={15} />
                  <p>
                    {pythonMode
                      ? "Your document is processed by this app’s Python server. Your library and progress stay in this browser."
                      : "Your documents stay in this browser. No account, no uploads, just you and your ideas."}
                  </p>
                </div>
                <div className="format-note">
                  PDF bookmarks become sections automatically. No bookmarks? We
                  make manageable groups you can edit.
                  <br />
                  <br />
                  PowerPoint imports as text cards. For original layouts and
                  images, export to PDF first.
                </div>
              </>
            ) : modal === "help" ? (
              <>
                <span className="modal-symbol">
                  <CircleHelp size={25} />
                </span>
                <div className="eyebrow">MAKE YOURSELF AT HOME</div>
                <h2>A little guide.</h2>
                <p>Learning, with a little less friction.</p>
                <div className="help-rows">
                  <div>
                    <span className="key-cap">←</span>
                    <div>
                      <strong>Feeling confident?</strong>
                      <p>Swipe left. You know this one.</p>
                    </div>
                  </div>
                  <div>
                    <span className="key-cap">→</span>
                    <div>
                      <strong>Worth another look?</strong>
                      <p>Swipe right to add it to your revisit pile.</p>
                    </div>
                  </div>
                  <div>
                    <span className="key-cap">Z</span>
                    <div>
                      <strong>Changed your mind?</strong>
                      <p>Undo your last swipe, any time.</p>
                    </div>
                  </div>
                  <div>
                    <span className="help-icon">
                      <BookOpen size={20} />
                    </span>
                    <div>
                      <strong>One section at a time.</strong>
                      <p>
                        See every slide to unlock the next section. Your saved
                        slides are waiting for a second look whenever you’re
                        ready.
                      </p>
                    </div>
                  </div>
                </div>
                <button
                  className="primary-button full"
                  onClick={() => setModal(null)}
                >
                  Got it. Let’s make it stick. <ArrowRight size={16} />
                </button>
              </>
            ) : modal === "sections" ? (
              <>
                <span className="modal-symbol">
                  <Layers3 size={24} />
                </span>
                <div className="eyebrow">MAKE IT MANAGEABLE</div>
                <h2>Your study path.</h2>
                <p>
                  Choose where each section begins. Every page stays in order.
                </p>
                <div className="section-edit-heading">
                  <span>SECTION NAME</span>
                  <span>START PAGE</span>
                </div>
                <div className="section-edit-list">
                  {sectionEdits.map((s, i) => (
                    <div className="section-edit-row" key={i}>
                      <span>{String(i + 1).padStart(2, "0")}</span>
                      <input
                        aria-label={`Section ${i + 1} name`}
                        value={s.title}
                        onChange={(e) =>
                          setSectionEdits((items) =>
                            items.map((v, j) =>
                              i === j ? { ...v, title: e.target.value } : v,
                            ),
                          )
                        }
                      />
                      <input
                        aria-label={`Section ${i + 1} start page`}
                        type="number"
                        min="1"
                        max={deck.slides.length}
                        disabled={!i}
                        value={s.start}
                        onChange={(e) =>
                          setSectionEdits((items) =>
                            items.map((v, j) =>
                              i === j
                                ? { ...v, start: Number(e.target.value) }
                                : v,
                            ),
                          )
                        }
                      />
                      <button
                        className="icon-button"
                        aria-label={`Remove section ${i + 1}`}
                        disabled={!i}
                        onClick={() =>
                          setSectionEdits((items) =>
                            items.filter((_, j) => i !== j),
                          )
                        }
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  className="text-button add-section"
                  disabled={
                    sectionEdits[sectionEdits.length - 1]?.start >=
                    deck.slides.length
                  }
                  onClick={() =>
                    setSectionEdits((items) => [
                      ...items,
                      {
                        title: `Section ${items.length + 1}`,
                        start: Math.min(
                          deck.slides.length,
                          items[items.length - 1].start + 5,
                        ),
                      },
                    ])
                  }
                >
                  <Plus size={15} />
                  Add a section
                </button>
                {sectionError && (
                  <p className="error-message" role="alert">
                    {sectionError}
                  </p>
                )}
                <button className="primary-button full" onClick={saveSections}>
                  Save my study path <Check size={17} />
                </button>
              </>
            ) : modal === "sound" ? (
              <>
                <span className="modal-symbol">
                  <Volume2 size={24} />
                </span>
                <div className="eyebrow">A SOFTER KIND OF FOCUS</div>
                <h2>A little atmosphere.</h2>
                <p>
                  A soft swish for each swipe. A little chime for each win.
                  Always at your volume.
                </p>
                <div className="sound-setting-row">
                  <div>
                    <strong>Study sounds</strong>
                    <p>
                      {sound.enabled
                        ? "A little company for your study session."
                        : "Quiet by default. Ready when you are."}
                    </p>
                  </div>
                  <button
                    className={`sound-switch ${sound.enabled ? "on" : ""}`}
                    role="switch"
                    aria-label="Study sounds"
                    aria-checked={sound.enabled}
                    onClick={() => {
                      sound.setEnabled(!sound.enabled);
                      if (!sound.enabled) sound.play("preview");
                    }}
                  >
                    <span />
                  </button>
                </div>
                <label className="volume-control" htmlFor="study-volume">
                  <span>
                    Just the right volume{" "}
                    <b>{Math.round(sound.volume * 100)}%</b>
                  </span>
                  <input
                    id="study-volume"
                    type="range"
                    min="0"
                    max="100"
                    value={Math.round(sound.volume * 100)}
                    onChange={(event) =>
                      sound.setVolume(Number(event.target.value) / 100)
                    }
                    aria-label="Sound volume"
                  />
                </label>
                <button
                  className="sound-preview"
                  disabled={!sound.enabled || sound.volume === 0}
                  onClick={() => sound.play("preview")}
                >
                  <Volume2 size={15} /> Hear a little preview
                </button>
                {sound.error && (
                  <p className="error-message" role="alert">
                    {sound.error}
                  </p>
                )}
                <div className="sound-footnote">
                  <Sparkles size={14} />
                  <span>
                    Gentle motion. Small celebrations. A little joy in the
                    process.
                  </span>
                </div>
                <button
                  className="primary-button full"
                  onClick={() => setModal(null)}
                >
                  That sounds good <Check size={16} />
                </button>
              </>
            ) : modal === "reset" ? (
              <>
                <span className="modal-symbol">
                  <RotateCcw size={24} />
                </span>
                <div className="eyebrow">A FRESH PAIR OF EYES</div>
                <h2>Begin again?</h2>
                <p>
                  This clears the swipe decisions and revisit pile for “
                  {deck.title}”. Your document and sections stay in your
                  library.
                </p>
                <button
                  className="primary-button full"
                  onClick={() => {
                    updateDeck({ ...deck, decisions: {}, revisited: [] });
                    setCheckpoint(null);
                    setReview(null);
                    setHistory([]);
                    setModal(null);
                    setToast("A fresh start. You’ve got this.");
                  }}
                >
                  Yes, give me a fresh start <RotateCcw size={16} />
                </button>
                <button
                  className="text-button full"
                  onClick={() => setModal(null)}
                >
                  Keep my progress
                </button>
              </>
            ) : (
              <>
                <span className="modal-symbol">
                  <Bookmark size={24} />
                </span>
                <div className="eyebrow">THE ONES WORTH COMING BACK TO</div>
                <h2>Your revisit pile.</h2>
                <p>
                  {saved.length
                    ? "A little uncertainty is a good place to start."
                    : "A little breathing room. Nothing saved just yet."}
                </p>
                {saved.length ? (
                  <>
                    <div className="saved-slides">
                      {saved.map((s) => (
                        <button key={s.id} onClick={() => startReview([s.id])}>
                          <span className="saved-page">
                            {String(s.page).padStart(2, "0")}
                          </span>
                          <span>{s.title}</span>
                          <ArrowUpRight size={16} />
                        </button>
                      ))}
                    </div>
                    <button
                      className="primary-button full"
                      onClick={() => startReview(saved.map((s) => s.id))}
                    >
                      Give {saved.length === 1 ? "it" : "them"} another look{" "}
                      <ArrowRight size={16} />
                    </button>
                  </>
                ) : (
                  <div className="empty-revisit">
                    <Bookmark size={40} strokeWidth={1} />
                    <p>
                      Swipe right on any slide to save it here.
                      <br />
                      It’ll be ready when you are.
                    </p>
                    <button
                      className="text-button"
                      onClick={() => setModal(null)}
                    >
                      Back to your slides <ArrowRight size={16} />
                    </button>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}
      {milestone && (
        <Celebration
          key={milestone.id}
          milestone={milestone}
          onFinish={finishCelebration}
        />
      )}
      {toast && (
        <div className="toast" role="status">
          <span>{toast}</span>
          <button
            aria-label="Dismiss notification"
            onClick={() => setToast("")}
          >
            <X size={15} />
          </button>
        </div>
      )}
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
