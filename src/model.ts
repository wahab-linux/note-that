export type Slide = {
  id: string;
  title: string;
  body: string;
  kicker?: string;
  image?: string;
  page?: number;
  art?: "spotlight" | "memory" | "focus";
};
export type Section = { id: string; title: string; start: number; end: number };
export type Decision = "confident" | "revisit";
export type Deck = {
  id: string;
  title: string;
  filename: string;
  slides: Slide[];
  sections: Section[];
  decisions: Record<string, Decision>;
  revisited: string[];
  created: number;
  kind: "demo" | "pdf" | "pptx" | "image";
};
import demo from "../data/demo.json";
export const demoDeck = demo as Deck;
const DB = "note-that-library";
function database(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () =>
      req.result.createObjectStore("decks", { keyPath: "id" });
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
export async function loadDecks(): Promise<Deck[]> {
  const db = await database();
  return new Promise((resolve, reject) => {
    const tx = db.transaction("decks", "readonly");
    const req = tx.objectStore("decks").getAll();
    req.onsuccess = () => {
      resolve(req.result);
      db.close();
    };
    req.onerror = () => {
      reject(req.error);
      db.close();
    };
  });
}
export async function saveDeck(deck: Deck) {
  const db = await database();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction("decks", "readwrite");
    tx.objectStore("decks").put(deck);
    tx.oncomplete = () => {
      resolve();
      db.close();
    };
    tx.onerror = () => {
      reject(tx.error);
      db.close();
    };
  });
}
export async function deleteDeck(id: string) {
  const db = await database();
  return new Promise<void>((resolve, reject) => {
    const tx = db.transaction("decks", "readwrite");
    tx.objectStore("decks").delete(id);
    tx.oncomplete = () => {
      resolve();
      db.close();
    };
    tx.onerror = () => {
      reject(tx.error);
      db.close();
    };
  });
}
export function sectionDone(deck: Deck, section: Section) {
  return deck.slides
    .slice(section.start, section.end + 1)
    .every((s) => deck.decisions[s.id]);
}
export function nextSection(deck: Deck) {
  return deck.sections.findIndex((s) => !sectionDone(deck, s));
}
