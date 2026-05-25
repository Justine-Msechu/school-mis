/** Download any 2-D array as a CSV file. */
export function downloadCSV(filename: string, headers: string[], rows: (string | number | null | undefined)[][]) {
  const escape = (v: string | number | null | undefined) => {
    const s = v == null ? "" : String(v);
    return s.includes(",") || s.includes('"') || s.includes("\n")
      ? `"${s.replace(/"/g, '""')}"`
      : s;
  };
  const csv = [headers, ...rows].map((r) => r.map(escape).join(",")).join("\r\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename.endsWith(".csv") ? filename : `${filename}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/** Open a new window and print HTML content. */
export function printHTML(title: string, bodyHtml: string) {
  const win = window.open("", "_blank", "width=900,height=700");
  if (!win) return;
  win.document.write(`<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8"/>
  <title>${title}</title>
  <style>
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body { font-family: Arial, sans-serif; font-size: 11px; color: #000; padding: 20px; }
    h1 { font-size: 15px; margin-bottom: 4px; }
    h2 { font-size: 13px; margin-bottom: 10px; color: #444; }
    .meta { font-size: 10px; color: #666; margin-bottom: 14px; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; }
    th { background: #f3f4f6; font-size: 9px; text-transform: uppercase; padding: 5px 6px; border: 1px solid #d1d5db; text-align: left; }
    td { padding: 4px 6px; border: 1px solid #e5e7eb; vertical-align: top; }
    tr:nth-child(even) td { background: #f9fafb; }
    .right { text-align: right; }
    .center { text-align: center; }
    .bold { font-weight: bold; }
    @media print { body { padding: 10px; } }
  </style>
</head>
<body>
  ${bodyHtml}
  <script>window.onload = function(){ window.print(); }<\/script>
</body>
</html>`);
  win.document.close();
}
