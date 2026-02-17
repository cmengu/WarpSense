/**
 * CSV generation and download utilities for supervisor export.
 */

/**
 * Generate CSV string from array of record objects.
 * Escapes quotes in values per RFC 4180.
 */
export function generateCSV(
  rows: Record<string, string | number>[]
): string {
  if (rows.length === 0) return '';
  const header = Object.keys(rows[0]).join(',');
  const body = rows
    .map((r) =>
      Object.values(r)
        .map((v) => `"${String(v).replace(/"/g, '""')}"`)
        .join(',')
    )
    .join('\n');
  return header + '\n' + body;
}

/**
 * Trigger browser download of CSV file.
 */
export function downloadCSV(filename: string, csv: string): void {
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
