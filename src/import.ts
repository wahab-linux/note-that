import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import JSZip from "jszip";
import type { Deck, Section, Slide } from "./model";
pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;
function defaultSections(count: number): Section[] {
  return Array.from({ length: Math.ceil(count / 5) }, (_, i) => ({
    id: `section-${i}`,
    title: count <= 5 ? "Your slides" : `Section ${i + 1}`,
    start: i * 5,
    end: Math.min(count - 1, i * 5 + 4),
  }));
}
export async function importDocument(
  file: File,
  progress: (message: string) => void,
): Promise<Deck> {
  if (file.size > 100 * 1024 * 1024)
    throw new Error(
      "That file is a little large. Please choose a file under 100 MB.",
    );
  const ext = file.name.split(".").pop()?.toLowerCase();
  const deck: Deck = {
    id: crypto.randomUUID(),
    title: file.name.replace(/\.[^.]+$/, "").replace(/[_-]/g, " "),
    filename: file.name,
    slides: [],
    sections: [],
    decisions: {},
    revisited: [],
    created: Date.now(),
    kind: "pdf",
  };
  if (ext === "pdf") {
    const pdf = await pdfjs.getDocument({
      data: new Uint8Array(await file.arrayBuffer()),
    }).promise;
    if (pdf.numPages > 300) {
      await pdf.destroy();
      throw new Error(
        "Please split this PDF into documents of 300 pages or fewer.",
      );
    }
    try {
      for (let i = 1; i <= pdf.numPages; i++) {
        progress(`Preparing page ${i} of ${pdf.numPages}…`);
        const page = await pdf.getPage(i);
        const base = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({
          scale: Math.min(1.7, 1500 / base.width),
        });
        const canvas = document.createElement("canvas");
        canvas.width = viewport.width;
        canvas.height = viewport.height;
        const context = canvas.getContext("2d");
        if (!context)
          throw new Error("Your browser could not render this PDF.");
        await page.render({ canvasContext: context, viewport, canvas }).promise;
        const text = await page.getTextContent();
        const title =
          text.items
            .filter((t) => "str" in t)
            .map((t) => ("str" in t ? t.str : ""))
            .join(" ")
            .trim()
            .slice(0, 100) || `Page ${i}`;
        deck.slides.push({
          id: `${deck.id}-${i}`,
          title,
          body: "",
          page: i,
          image: canvas.toDataURL("image/webp", 0.85),
        });
        page.cleanup();
      }
      const outline = await pdf.getOutline();
      const starts: { title: string; page: number }[] = [];
      if (outline)
        for (const item of outline) {
          let destination = item.dest;
          if (typeof destination === "string")
            destination = await pdf.getDestination(destination);
          if (Array.isArray(destination) && destination[0] !== undefined) {
            const page =
              typeof destination[0] === "number"
                ? destination[0]
                : await pdf.getPageIndex(destination[0]);
            if (page >= 0 && page < pdf.numPages)
              starts.push({ title: item.title, page });
          }
        }
      const sorted = starts
        .sort((a, b) => a.page - b.page)
        .filter((s, i, all) => !i || s.page !== all[i - 1].page);
      if (sorted.length) {
        if (sorted[0].page > 0)
          sorted.unshift({ title: "Introduction", page: 0 });
        deck.sections = sorted.map((s, i) => ({
          id: `section-${i}`,
          title: s.title,
          start: s.page,
          end: (sorted[i + 1]?.page ?? deck.slides.length) - 1,
        }));
      }
    } finally {
      await pdf.destroy();
    }
  } else if (ext === "pptx") {
    deck.kind = "pptx";
    progress("Reading your presentation…");
    const zip = await JSZip.loadAsync(file);
    const paths = Object.keys(zip.files)
      .filter((p) => /^ppt\/slides\/slide\d+\.xml$/.test(p))
      .sort(
        (a, b) =>
          Number(a.match(/slide(\d+)/)?.[1]) -
          Number(b.match(/slide(\d+)/)?.[1]),
      );
    if (!paths.length || paths.length > 300)
      throw new Error("Please use a presentation with 1–300 slides.");
    for (const [i, path] of paths.entries()) {
      const xml = new DOMParser().parseFromString(
        await zip.files[path].async("text"),
        "application/xml",
      );
      const paragraphs = [...xml.getElementsByTagNameNS("*", "p")]
        .map((p) =>
          [...p.getElementsByTagNameNS("*", "t")]
            .map((t) => t.textContent)
            .join(""),
        )
        .filter(Boolean);
      deck.slides.push({
        id: `${deck.id}-${i}`,
        title: paragraphs[0] || `Slide ${i + 1}`,
        body:
          paragraphs.slice(1).join("\n\n") ||
          (paragraphs.length
            ? ""
            : "This slide has no text. Export your presentation as PDF to study its visual content."),
        page: i + 1,
      });
    }
  } else if (["png", "jpg", "jpeg", "webp"].includes(ext || "")) {
    deck.kind = "image";
    const image = await new Promise<string>((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(String(reader.result));
      reader.onerror = () => reject(new Error("Could not read this image."));
      reader.readAsDataURL(file);
    });
    deck.slides = [
      { id: `${deck.id}-1`, title: deck.title, body: "", image, page: 1 },
    ];
  } else throw new Error("Choose a PDF, PowerPoint (.pptx), or slide image.");
  if (!deck.slides.length)
    throw new Error("This document does not contain any slides.");
  if (!deck.sections.length)
    deck.sections = defaultSections(deck.slides.length);
  return deck;
}
