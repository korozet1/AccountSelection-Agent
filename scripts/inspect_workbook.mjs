import { FileBlob, SpreadsheetFile } from "@oai/artifact-tool";

const inputPath = "D:/Program Files (x86)/Tencent/Wechat/xwechat_files/wxid_1oszneloqxon12_5660/msg/file/2026-05/YXC-PM-02-EXCEL 操作测试题 (1).xlsx";

const input = await FileBlob.load(inputPath);
const workbook = await SpreadsheetFile.importXlsx(input);

const summary = await workbook.inspect({
  kind: "workbook,sheet,table,region,formula",
  maxChars: 12000,
  tableMaxRows: 20,
  tableMaxCols: 20,
  tableMaxCellChars: 80,
});
console.log(summary.ndjson);

const sheets = await workbook.inspect({ kind: "sheet", include: "id,name", maxChars: 2000 });
console.log("SHEETS");
console.log(sheets.ndjson);
