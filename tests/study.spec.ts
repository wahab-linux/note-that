import { test, expect } from "@playwright/test";
import JSZip from "jszip";
function pdfFixture() {
  const objects: string[] = [
    "<< /Type /Catalog /Pages 2 0 R /Outlines 18 0 R >>",
    "<< /Type /Pages /Kids [3 0 R 5 0 R 7 0 R 9 0 R 11 0 R 13 0 R 15 0 R] /Count 7 >>",
  ];
  for (let i = 0; i < 7; i++) {
    const contents = `BT /F1 28 Tf 45 220 Td (Focus slide ${i + 1}) Tj ET`;
    objects.push(
      `<< /Type /Page /Parent 2 0 R /MediaBox [0 0 500 300] /Resources << /Font << /F1 17 0 R >> >> /Contents ${4 + i * 2} 0 R >>`,
    );
    objects.push(
      `<< /Length ${contents.length} >>\nstream\n${contents}\nendstream`,
    );
  }
  objects.push("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>");
  objects.push("<< /Type /Outlines /First 19 0 R /Last 20 0 R /Count 2 >>");
  objects.push(
    "<< /Title (Getting started) /Parent 18 0 R /Next 20 0 R /Dest [3 0 R /Fit] >>",
  );
  objects.push(
    "<< /Title (Going deeper) /Parent 18 0 R /Prev 19 0 R /Dest [9 0 R /Fit] >>",
  );
  let pdf = "%PDF-1.7\n";
  const offsets = [0];
  objects.forEach((body, i) => {
    offsets.push(Buffer.byteLength(pdf));
    pdf += `${i + 1} 0 obj\n${body}\nendobj\n`;
  });
  const xref = Buffer.byteLength(pdf);
  pdf += `xref\n0 ${objects.length + 1}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1))
    pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  pdf += `trailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xref}\n%%EOF`;
  return Buffer.from(pdf);
}
async function ready(page: import("@playwright/test").Page) {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: "Attention is a spotlight." }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: /I know this/ })).toBeEnabled();
}

test("swipes, undo, persisted progress, section locks, and revisit sessions work together", async ({
  page,
}) => {
  await ready(page);
  await expect(
    page.getByRole("button", { name: /How memory works/ }),
  ).toBeDisabled();
  await page.keyboard.press("ArrowRight");
  await expect(
    page.getByRole("heading", { name: "Your mind has a filter." }),
  ).toBeVisible();
  await expect(page.locator(".revisit-strip strong")).toHaveText(
    "Your revisit pile 1",
  );
  await page.keyboard.press("z");
  await expect(
    page.getByRole("heading", { name: "Attention is a spotlight." }),
  ).toBeVisible();
  await expect(page.locator(".revisit-strip strong")).toHaveText(
    "Your revisit pile 0",
  );
  await page.getByRole("button", { name: /Revisit later/ }).click();
  await expect(
    page.getByRole("heading", { name: "Your mind has a filter." }),
  ).toBeVisible();
  await expect(page.getByText("Your progress is saved")).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your mind has a filter." }),
  ).toBeVisible();
  for (const title of [
    "One thing at a time.",
    "Notice what you notice.",
    "Give your mind a moment.",
    "Section, sorted.",
  ]) {
    await page.getByRole("button", { name: /I know this/ }).click();
    await expect(page.getByRole("heading", { name: title })).toBeVisible();
  }
  await page.getByRole("button", { name: "Revisit 1 saved slides" }).click();
  await expect(
    page.getByRole("heading", { name: "Attention is a spotlight." }),
  ).toBeVisible();
  await page.getByRole("button", { name: /I know this/ }).click();
  await expect(
    page.getByRole("heading", { name: "That’s your second look." }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Back to my study path/ }).click();
  await page.getByRole("button", { name: /On to the next section/ }).click();
  await expect(
    page.getByRole("heading", { name: "Memory is a process." }),
  ).toBeVisible();
  await expect(page.locator(".revisit-strip strong")).toHaveText(
    "Your revisit pile 0",
  );
  await page
    .getByRole("button", { name: "Your progress", exact: true })
    .click();
  await expect(page.locator(".big-stat").nth(0).locator("strong")).toHaveText(
    "5",
  );
  await expect(page.locator(".big-stat").nth(1).locator("strong")).toHaveText(
    "5",
  );
});

test("PDF import renders actual pages, discovers sections, persists, and permits section editing", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await ready(page);
  await page.getByRole("button", { name: /Import a document/ }).click();
  await page.getByLabel("Choose a document").setInputFiles({
    name: "Focus notes.pdf",
    mimeType: "application/pdf",
    buffer: pdfFixture(),
  });
  await expect(page.locator(".document-selector strong")).toHaveText(
    "Focus notes",
    { timeout: 20000 },
  );
  await expect(page.locator(".document-meta")).toHaveText(
    "7 slides · 2 sections",
  );
  await expect(page.locator(".image-slide img")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Getting started/ }),
  ).toBeEnabled();
  await expect(
    page.getByRole("button", { name: /Going deeper/ }),
  ).toBeDisabled();
  const loadedImage = await page
    .locator(".image-slide img")
    .evaluate(
      (img: HTMLImageElement) => img.complete && img.naturalWidth > 100,
    );
  expect(loadedImage).toBe(true);
  await page.getByRole("button", { name: "Enlarge slide" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await page.keyboard.press("Escape");
  await page.getByRole("button", { name: /I know this/ }).click();
  await expect(page.locator(".slide-count")).toContainText("2 / 3 slides");
  await expect(page.getByText("Your progress is saved")).toBeVisible();
  await page.reload();
  await expect(page.locator(".document-selector strong")).toHaveText(
    "Focus notes",
  );
  await expect(page.locator(".slide-count")).toContainText("2 / 3 slides");
  await page.getByRole("button", { name: "Edit sections" }).click();
  await page.getByLabel("Section 1 name").fill("The basics");
  await page.getByRole("button", { name: /Save my study path/ }).click();
  await expect(page.getByRole("button", { name: /The basics/ })).toBeVisible();
  await page.getByRole("button", { name: "My library" }).click();
  await page.getByLabel("Find a document").fill("Focus");
  await expect(page.locator(".deck-tile")).toHaveCount(1);
  expect(errors).toEqual([]);
});

test("PowerPoint text import and unsupported file errors are usable", async ({
  page,
}) => {
  await ready(page);
  await page.getByRole("button", { name: /Import a document/ }).click();
  await page.getByLabel("Choose a document").setInputFiles({
    name: "notes.txt",
    mimeType: "text/plain",
    buffer: Buffer.from("hello"),
  });
  await expect(page.getByRole("alert")).toHaveText(
    "Choose a PDF, PowerPoint (.pptx), or slide image.",
  );
  const zip = new JSZip();
  zip.file(
    "ppt/slides/slide1.xml",
    '<p:sld xmlns:p="p" xmlns:a="a"><a:p><a:r><a:t>A focused mind</a:t></a:r></a:p><a:p><a:r><a:t>Start with one small thing.</a:t></a:r></a:p></p:sld>',
  );
  await page.getByLabel("Choose a document").setInputFiles({
    name: "My slides.pptx",
    mimeType:
      "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    buffer: await zip.generateAsync({ type: "nodebuffer" }),
  });
  await expect(
    page.getByRole("heading", { name: "A focused mind" }),
  ).toBeVisible();
  await expect(page.getByText("Start with one small thing.")).toBeVisible();
  await page.getByRole("button", { name: /I know this/ }).click();
  await expect(
    page.getByRole("heading", { name: "Section, sorted." }),
  ).toBeVisible();
  await page.getByRole("button", { name: /Finish this session/ }).click();
  await expect(
    page.getByRole("heading", { name: "You made it through." }),
  ).toBeVisible();
});

test("phone layout fits the viewport and supports touch-style swipes and dialogs", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await ready(page);
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  const card = page.locator(".study-card");
  const box = (await card.boundingBox())!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  await page.mouse.down();
  await page.mouse.move(box.x + box.width / 2 + 120, box.y + box.height / 2, {
    steps: 8,
  });
  await page.mouse.up();
  await expect(
    page.getByRole("heading", { name: "Your mind has a filter." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Take a look" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(
    page.getByRole("button", { name: /Give it another look/ }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Close dialog" }).click();
  await expect(page.getByRole("dialog")).not.toBeVisible();
  await page.getByRole("button", { name: "My library", exact: true }).click();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("sound is opt-in, plays audio, remembers volume, and stops when muted", async ({
  page,
}) => {
  await page.addInitScript(() => {
    (window as any).__audioStarts = 0;
    const original = AudioContext.prototype.createOscillator;
    AudioContext.prototype.createOscillator = function () {
      const oscillator = original.call(this);
      const start = oscillator.start.bind(oscillator);
      oscillator.start = (...args) => {
        (window as any).__audioStarts++;
        start(...args);
      };
      return oscillator;
    };
  });
  await ready(page);
  expect(await page.evaluate(() => (window as any).__audioStarts)).toBe(0);
  await page.getByRole("button", { name: "Sound settings" }).click();
  await expect(
    page.getByRole("switch", { name: "Study sounds" }),
  ).not.toBeChecked();
  await page.getByRole("switch", { name: "Study sounds" }).click();
  await expect
    .poll(() => page.evaluate(() => (window as any).__audioStarts))
    .toBeGreaterThanOrEqual(3);
  await page.getByLabel("Sound volume").fill("55");
  await page.getByRole("button", { name: /That sounds good/ }).click();
  await page.reload();
  await page.getByRole("button", { name: "Sound settings" }).click();
  await expect(
    page.getByRole("switch", { name: "Study sounds" }),
  ).toBeChecked();
  await expect(page.getByLabel("Sound volume")).toHaveValue("55");
  await page.getByRole("button", { name: /Hear a little preview/ }).click();
  await expect
    .poll(() => page.evaluate(() => (window as any).__audioStarts))
    .toBeGreaterThanOrEqual(3);
  await page.getByRole("switch", { name: "Study sounds" }).click();
  const before = await page.evaluate(() => (window as any).__audioStarts);
  await page.getByRole("button", { name: "Close dialog" }).click();
  await page.getByRole("button", { name: /I know this/ }).click();
  await expect(
    page.getByRole("heading", { name: "Your mind has a filter." }),
  ).toBeVisible();
  expect(await page.evaluate(() => (window as any).__audioStarts)).toBe(before);
});

test("a real PDF celebrates sections and the entire document with rendered confetti", async ({
  page,
}) => {
  await ready(page);
  await page.getByRole("button", { name: /Import a document/ }).click();
  const imported = page.waitForResponse(
    (response) =>
      response.url().endsWith("/api/import") &&
      response.request().method() === "POST",
  );
  await page
    .getByLabel("Choose a document")
    .setInputFiles({
      name: "Every little page.pdf",
      mimeType: "application/pdf",
      buffer: pdfFixture(),
    });
  expect((await imported).status()).toBe(200);
  await expect(page.locator(".document-selector strong")).toHaveText(
    "Every little page",
  );
  for (let i = 0; i < 3; i++) {
    await page.getByRole("button", { name: /I know this/ }).click();
    if (i < 2)
      await expect(page.locator(".slide-count")).toContainText(
        `${i + 2} / 3 slides`,
      );
  }
  await expect(
    page.getByRole("heading", { name: "Section, sorted." }),
  ).toBeVisible();
  await expect(page.getByTestId("celebration")).toHaveAttribute(
    "data-kind",
    "section",
  );
  await expect
    .poll(() =>
      page
        .locator(".celebration canvas")
        .evaluate((canvas: HTMLCanvasElement) => {
          const pixels = canvas
            .getContext("2d")!
            .getImageData(0, 0, canvas.width, canvas.height).data;
          return pixels.some((value, i) => i % 4 === 3 && value > 0);
        }),
    )
    .toBe(true);
  await page.getByRole("button", { name: /On to the next section/ }).click();
  for (let i = 0; i < 4; i++) {
    await page.getByRole("button", { name: /I know this/ }).click();
    if (i < 3)
      await expect(page.locator(".slide-count")).toContainText(
        `${i + 2} / 4 slides`,
      );
  }
  await expect(
    page.getByRole("heading", { name: "Section, sorted." }),
  ).toBeVisible();
  await expect(page.getByTestId("celebration")).toHaveAttribute(
    "data-kind",
    "document",
  );
  await page.getByRole("button", { name: /Finish this session/ }).click();
  await expect(
    page.getByRole("heading", { name: "You made it through." }),
  ).toBeVisible();
});

test("reduced motion keeps celebrations still and theme choice survives reload", async ({
  page,
}) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await ready(page);
  await page.getByRole("button", { name: "Switch to dark mode" }).click();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.reload();
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await page.getByRole("button", { name: "Switch to light mode" }).click();
  for (let i = 0; i < 5; i++) {
    await page.getByRole("button", { name: /I know this/ }).click();
    if (i < 4)
      await expect(page.locator(".slide-count")).toContainText(
        `${i + 2} / 5 slides`,
      );
  }
  await expect(page.getByTestId("celebration")).toBeVisible();
  await expect(page.locator(".celebration canvas")).toHaveCount(0);
});
