import fs from "node:fs/promises";
import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/Program Files (x86)/Tencent/Wechat/xwechat_files/wxid_1oszneloqxon12_5660/msg/file/2026-05/YXC-PM-02-EXCEL 操作测试题 (1).xlsx";
const outputDir = "outputs/excel_test";
const outputPath = `${outputDir}/YXC-PM-02-EXCEL 操作测试题-完成版.xlsx`;
const previewPath = `${outputDir}/一月表预览.png`;

await fs.mkdir(outputDir, { recursive: true });

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const sourceSheet = workbook.worksheets.getItem("Sheet1");
const targetSheet = workbook.worksheets.getItem("Sheet2");

targetSheet.name = "一月表";
targetSheet.showGridLines = true;

const sourceRange = sourceSheet.getRange("A1:H7");
const targetRange = targetSheet.getRange("A1:H7");
targetRange.clear({ applyTo: "all" });
targetRange.copyFrom(sourceRange, "values");

const title = targetSheet.getRange("A1:H1");
title.merge();
title.format = {
  font: {
    name: "黑体",
    bold: true,
    size: 20,
    color: "#000000",
  },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
targetSheet.getRange("A1:H1").format.rowHeightPx = 38;

const header = targetSheet.getRange("A2:H2");
header.format = {
  fill: "#D9D9D9",
  font: { bold: true, color: "#000000" },
  horizontalAlignment: "center",
  verticalAlignment: "center",
};

targetSheet.getRange("B3:B7").format = {
  fill: "#00B0F0",
  horizontalAlignment: "center",
  verticalAlignment: "center",
};

targetSheet.getRange("A3:A7").format = {
  fill: "#FFFF00",
  horizontalAlignment: "center",
  verticalAlignment: "center",
};
targetSheet.getRange("C3:H7").format = {
  fill: "#FFFF00",
  horizontalAlignment: "center",
  verticalAlignment: "center",
};

targetSheet.getRange("F3").formulas = [["=C3+D3+E3"]];
targetSheet.getRange("F3:F7").fillDown();
targetSheet.getRange("G3").formulas = [["=(F3-1000)*0.05"]];
targetSheet.getRange("G3:G7").fillDown();

targetSheet.getRange("A1:H7").format = {
  ...targetSheet.getRange("A1:H7").format,
  wrapText: false,
};

targetSheet.getRange("A:H").format.columnWidthPx = 92;
targetSheet.getRange("A:A").format.columnWidthPx = 70;
targetSheet.getRange("B:B").format.columnWidthPx = 80;
targetSheet.getRange("F:H").format.columnWidthPx = 92;
targetSheet.getRange("A2:H7").format.rowHeightPx = 26;
targetSheet.getRange("C3:H7").format.numberFormat = "#,##0.00";
targetSheet.getRange("A3:A7").format.numberFormat = "0";
targetSheet.getRange("D3:D7").format.numberFormat = "0";

const check = await workbook.inspect({
  kind: "table,formula,computedStyle",
  sheetId: "一月表",
  range: "A1:H7",
  include: "values,formulas",
  tableMaxRows: 10,
  tableMaxCols: 10,
  maxChars: 8000,
});
console.log(check.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "final formula error scan",
  maxChars: 4000,
});
console.log("ERROR_SCAN");
console.log(errors.ndjson);

const preview = await workbook.render({
  sheetName: "一月表",
  range: "A1:H7",
  scale: 2,
  format: "png",
});
await fs.writeFile(previewPath, new Uint8Array(await preview.arrayBuffer()));

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
console.log(`OUTPUT=${outputPath}`);
console.log(`PREVIEW=${previewPath}`);
