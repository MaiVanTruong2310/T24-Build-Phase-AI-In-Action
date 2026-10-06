import { Service } from './api';

function csvCell(value: string | number | null): string {
  let text = value == null ? '' : String(value);
  if (/^[\t\r ]*[=+\-@]/.test(text)) text = `'${text}`;
  return `"${text.replaceAll('"', '""')}"`;
}

export function serializeServicesCsv(services: Service[]): string {
  const rows = [
    ['Code', 'Name', 'Description', 'Category', 'Price', 'Duration (minutes)', 'Status'],
    ...services.map((service) => [
      service.code,
      service.name,
      service.description,
      service.category,
      service.price,
      service.duration_minutes,
      service.status,
    ]),
  ];
  return '\uFEFF' + rows.map((row) => row.map(csvCell).join(',')).join('\r\n');
}

export function exportServicesCsv(services: Service[]): void {
  const csv = serializeServicesCsv(services);
  const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
  const link = document.createElement('a');
  link.href = url;
  link.download = 'dich-vu.csv';
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}
