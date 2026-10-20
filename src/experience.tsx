import { useEffect, useRef, useState, type ReactNode } from "react";
import {
  motion,
  useMotionValue,
  useReducedMotion,
  useTransform,
} from "motion/react";
import type { Decision } from "./model";

type Sound = "confident" | "revisit" | "section" | "document" | "preview";
type Preferences = { enabled: boolean; volume: number };
const SETTINGS = "note-that-sound";
function readPreferences(): Preferences {
  try {
    const data = JSON.parse(localStorage.getItem(SETTINGS) || "{}");
    return {
      enabled: data.enabled === true,
      volume:
        typeof data.volume === "number"
          ? Math.max(0, Math.min(1, data.volume))
          : 0.35,
    };
  } catch {
    return { enabled: false, volume: 0.35 };
  }
}
class SoftAudio {
  context: AudioContext | null = null;
  async play(kind: Sound, preferences: Preferences, preview = false) {
    if ((!preferences.enabled && !preview) || preferences.volume === 0) return;
    this.context ??= new AudioContext();
    const context = this.context;
    if (context.state === "suspended") await context.resume();
    if (this.context !== context || context.state === "closed") return;
    const now = context.currentTime;
    // Smooth envelopes prevent clicks; no audio files or external requests.
    const note = (
      frequency: number,
      delay: number,
      duration: number,
      amplitude: number,
    ) => {
      const oscillator = context.createOscillator();
      const gain = context.createGain();
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(frequency, now + delay);
      oscillator.frequency.exponentialRampToValueAtTime(
        frequency * 0.985,
        now + delay + duration,
      );
      gain.gain.setValueAtTime(0.0001, now + delay);
      gain.gain.exponentialRampToValueAtTime(
        Math.max(0.0002, amplitude * preferences.volume),
        now + delay + 0.025,
      );
      gain.gain.exponentialRampToValueAtTime(0.0001, now + delay + duration);
      oscillator.connect(gain);
      gain.connect(context.destination);
      oscillator.start(now + delay);
      oscillator.stop(now + delay + duration + 0.02);
      oscillator.onended = () => {
        oscillator.disconnect();
        gain.disconnect();
      };
    };
    if (kind === "section" || kind === "document" || kind === "preview") {
      const notes =
        kind === "document"
          ? [523.25, 659.25, 783.99, 1046.5]
          : [523.25, 659.25, 783.99];
      notes.forEach((frequency, i) => note(frequency, i * 0.105, 0.65, 0.095));
      return;
    }
    const duration = 0.22;
    const length = Math.ceil(context.sampleRate * duration);
    const buffer = context.createBuffer(1, length, context.sampleRate);
    const channel = buffer.getChannelData(0);
    for (let i = 0; i < length; i++) channel[i] = Math.random() * 2 - 1;
    const source = context.createBufferSource();
    source.buffer = buffer;
    const filter = context.createBiquadFilter();
    filter.type = "lowpass";
    filter.Q.value = 0.3;
    filter.frequency.setValueAtTime(kind === "confident" ? 780 : 610, now);
    filter.frequency.exponentialRampToValueAtTime(170, now + duration);
    const envelope = context.createGain();
    envelope.gain.setValueAtTime(0.0001, now);
    envelope.gain.exponentialRampToValueAtTime(
      Math.max(0.0002, 0.17 * preferences.volume),
      now + 0.055,
    );
    envelope.gain.exponentialRampToValueAtTime(0.0001, now + duration);
    source.connect(filter);
    filter.connect(envelope);
    envelope.connect(context.destination);
    source.start(now);
    source.stop(now + duration);
    source.onended = () => {
      source.disconnect();
      filter.disconnect();
      envelope.disconnect();
    };
    note(kind === "confident" ? 392 : 329.63, 0.03, 0.25, 0.05);
  }
  dispose() {
    const context = this.context;
    this.context = null;
    if (context && context.state !== "closed") void context.close();
  }
}
export function useStudySound() {
  const [preferences, setPreferences] = useState(readPreferences);
  const [error, setError] = useState("");
  const engine = useRef(new SoftAudio());
  const current = useRef(preferences);
  current.current = preferences;
  useEffect(() => {
    try {
      localStorage.setItem(SETTINGS, JSON.stringify(preferences));
    } catch {
      /* Session settings still work. */
    }
  }, [preferences]);
  useEffect(() => () => engine.current.dispose(), []);
  function play(kind: Sound, preview = false) {
    if (typeof AudioContext === "undefined") {
      if (preview)
        setError(
          "Sound isn’t available in this browser. Your study session still works.",
        );
      return;
    }
    void engine.current
      .play(kind, current.current, preview)
      .catch(() =>
        setError(
          "Your browser paused audio. Try the preview button to enable it.",
        ),
      );
  }
  return {
    ...preferences,
    error,
    setEnabled: (enabled: boolean) => {
      current.current = { ...current.current, enabled };
      setPreferences(current.current);
      if (!enabled) engine.current.dispose();
    },
    setVolume: (volume: number) => {
      current.current = { ...current.current, volume };
      setPreferences(current.current);
    },
    play,
  };
}

const cardVariants = {
  enter: { opacity: 0, y: 16, scaleX: 0.94, scaleY: 1.055, rotate: -1.3 },
  center: {
    opacity: 1,
    y: 0,
    scaleX: 1,
    scaleY: 1,
    rotate: 0,
    transition: {
      type: "spring" as const,
      stiffness: 285,
      damping: 17,
      mass: 0.8,
    },
  },
  exit: (direction: number) => ({
    x: direction * 520,
    y: 16,
    rotate: direction * 13,
    scaleX: 0.96,
    scaleY: 1.035,
    opacity: 0,
    transition: { duration: 0.25, ease: [0.32, 0.02, 0.65, 1] as const },
  }),
};
export function JellyCard({
  children,
  image,
  onDecision,
  onReady,
  disabled,
}: {
  children: ReactNode;
  image: boolean;
  onDecision: (decision: Decision) => void;
  onReady: () => void;
  disabled: boolean;
}) {
  const x = useMotionValue(0);
  const rotate = useTransform(x, [-400, 400], [-11, 11]);
  const [offset, setOffset] = useState(0);
  const reduced = useReducedMotion();
  return (
    <motion.div
      className={`study-card jelly-card ${image ? "pdf-card" : ""}`}
      style={{ x, rotate }}
      variants={
        reduced
          ? {
              enter: { opacity: 0 },
              center: { opacity: 1, transition: { duration: 0.08 } },
              exit: { opacity: 0, transition: { duration: 0.08 } },
            }
          : cardVariants
      }
      initial="enter"
      animate="center"
      exit="exit"
      drag={disabled ? false : "x"}
      dragConstraints={{ left: 0, right: 0 }}
      dragElastic={0.82}
      dragMomentum={false}
      dragTransition={{ bounceStiffness: 420, bounceDamping: 22 }}
      onAnimationComplete={(definition) => {
        if (definition === "center") onReady();
      }}
      onDrag={(_, info) => setOffset(info.offset.x)}
      onDragEnd={(_, info) => {
        const crossed =
          Math.abs(info.offset.x) > 85 ||
          (Math.abs(info.offset.x) > 25 && Math.abs(info.velocity.x) > 650);
        if (crossed) onDecision(info.offset.x > 0 ? "revisit" : "confident");
        setOffset(0);
      }}
    >
      {children}
      {Math.abs(offset) > 30 && (
        <span className={`swipe-label ${offset > 0 ? "later" : "know"}`}>
          {offset > 0 ? "A second look" : "Got this ✓"}
        </span>
      )}
    </motion.div>
  );
}

export type Milestone = { id: number; kind: "section" | "document" };
export function Celebration({
  milestone,
  onFinish,
}: {
  milestone: Milestone;
  onFinish: () => void;
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const reduced = useReducedMotion();
  useEffect(() => {
    const duration = reduced
      ? 1700
      : milestone.kind === "document"
        ? 3500
        : 2600;
    const timeout = window.setTimeout(onFinish, duration);
    if (reduced || !canvas.current) return () => clearTimeout(timeout);
    const node = canvas.current;
    const context = node.getContext("2d");
    if (!context) return () => clearTimeout(timeout);
    let width = innerWidth,
      height = innerHeight;
    const ratio = Math.min(devicePixelRatio || 1, 2);
    function resize() {
      width = innerWidth;
      height = innerHeight;
      node.width = width * ratio;
      node.height = height * ratio;
      context!.setTransform(ratio, 0, 0, ratio, 0, 0);
    }
    resize();
    window.addEventListener("resize", resize);
    const colors = [
      "#b4503d",
      "#8a9b71",
      "#c1aa78",
      "#ddd2ac",
      "#e9b1a1",
      "#556a58",
    ];
    const pieces = Array.from(
      { length: milestone.kind === "document" ? 160 : 85 },
      (_, i) => ({
        x: width * (i % 2 ? 0.23 : 0.77),
        y: height * 0.52,
        vx: (Math.random() - 0.5) * 760,
        vy: -300 - Math.random() * 540,
        angle: Math.random() * Math.PI,
        spin: (Math.random() - 0.5) * 10,
        size: 4 + Math.random() * 6,
        color: colors[i % colors.length],
        phase: Math.random() * 6,
      }),
    );
    let frame = 0,
      previous = performance.now();
    const started = previous;
    function draw(now: number) {
      const dt = Math.min((now - previous) / 1000, 0.033);
      previous = now;
      context!.clearRect(0, 0, width, height);
      context!.globalAlpha = Math.max(
        0,
        Math.min(1, (duration - (now - started)) / 600),
      );
      for (const piece of pieces) {
        piece.vx *= Math.pow(0.98, dt * 60);
        piece.vy += 550 * dt;
        piece.x += piece.vx * dt;
        piece.y += piece.vy * dt;
        piece.angle += piece.spin * dt;
        context!.save();
        context!.translate(piece.x, piece.y);
        context!.rotate(piece.angle);
        context!.scale(
          1,
          0.3 + Math.abs(Math.sin(now / 180 + piece.phase)) * 0.7,
        );
        context!.fillStyle = piece.color;
        context!.fillRect(
          -piece.size / 2,
          -piece.size / 2,
          piece.size,
          piece.size * 0.62,
        );
        context!.restore();
      }
      frame = requestAnimationFrame(draw);
    }
    frame = requestAnimationFrame(draw);
    return () => {
      clearTimeout(timeout);
      cancelAnimationFrame(frame);
      window.removeEventListener("resize", resize);
      context.clearRect(0, 0, width, height);
    };
  }, [milestone.id, milestone.kind, reduced, onFinish]);
  return (
    <div
      className="celebration"
      data-testid="celebration"
      data-kind={milestone.kind}
      aria-live="polite"
      role="status"
    >
      {!reduced && <canvas ref={canvas} aria-hidden="true" />}
      <div className="celebration-note">
        <span>✳</span>
        {milestone.kind === "document"
          ? "Every page. One lovely little win."
          : "One section closer. Look at you go."}
      </div>
    </div>
  );
}
