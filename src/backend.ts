import type { Deck } from "./model";
let detection: Promise<boolean> | undefined;
export function hasPythonBackend(): Promise<boolean> {
  detection ??= fetch("/api/health", { signal: AbortSignal.timeout(2500) })
    .then(
      async (response) =>
        response.ok && (await response.json()).backend === "python",
    )
    .catch(() => false);
  return detection;
}
export async function openDocument(
  file: File,
  progress: (message: string) => void,
): Promise<Deck> {
  if (file.size > 100 * 1024 * 1024)
    throw new Error(
      "That file is a little large. Please choose a file under 100 MB.",
    );
  if (await hasPythonBackend()) {
    progress("Preparing your pages. A little moment…");
    const form = new FormData();
    form.append("file", file);
    const response = await fetch("/api/import", { method: "POST", body: form });
    const result = await response.json();
    if (!response.ok)
      throw new Error(
        typeof result.detail === "string"
          ? result.detail
          : "This file could not be opened. Please try another document.",
      );
    return result;
  }
  // Static hosting remains supported; the Python command uses the server importer.
  const { importDocument } = await import("./import");
  return importDocument(file, progress);
}
