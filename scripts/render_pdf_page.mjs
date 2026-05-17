import fs from "node:fs/promises";
import { createCanvas } from "@napi-rs/canvas";
import * as pdfjsLib from "pdfjs-dist/legacy/build/pdf.mjs";

const input = "inputs/data_check/reference.pdf";
const output = "outputs/data_check/pdf_render/page-1.png";

await fs.mkdir("outputs/data_check/pdf_render", { recursive: true });
const data = new Uint8Array(await fs.readFile(input));
const pdf = await pdfjsLib.getDocument({ data, disableWorker: true }).promise;
const page = await pdf.getPage(1);
const viewport = page.getViewport({ scale: 2.5 });
const canvas = createCanvas(Math.ceil(viewport.width), Math.ceil(viewport.height));
const context = canvas.getContext("2d");
await page.render({ canvasContext: context, viewport }).promise;
await fs.writeFile(output, canvas.toBuffer("image/png"));
console.log(output, canvas.width, canvas.height);
