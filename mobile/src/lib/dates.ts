const MONTHS = [
  "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
  "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
];
const WEEKDAYS = ["DOM", "SEG", "TER", "QUA", "QUI", "SEX", "SÁB"];

const pad = (n: number) => String(n).padStart(2, "0");

/** Data local no formato da API (YYYY-MM-DD). */
export function toISODate(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** "2026-10-12" -> Date local (meia-noite), sem problema de fuso. */
export function fromISODate(iso: string): Date {
  const [y, m, d] = iso.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function toMonthKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

export function shiftMonth(month: string, delta: number): string {
  const [y, m] = month.split("-").map(Number);
  return toMonthKey(new Date(y, m - 1 + delta, 1));
}

export function monthLabel(month: string): string {
  const [y, m] = month.split("-").map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

export function monthShort(month: string): string {
  return MONTHS[Number(month.split("-")[1]) - 1].slice(0, 3);
}

export function monthRange(month: string): { from: string; to: string } {
  const [y, m] = month.split("-").map(Number);
  return { from: `${month}-01`, to: `${month}-${pad(new Date(y, m, 0).getDate())}` };
}

export function formatDateBR(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}/${m}/${y}`;
}

/** "hoje", "ontem" ou "10/10". */
export function relativeDay(iso: string, today = new Date()): string {
  const todayIso = toISODate(today);
  const y = new Date(today);
  y.setDate(y.getDate() - 1);
  if (iso === todayIso) return "hoje";
  if (iso === toISODate(y)) return "ontem";
  return formatDateBR(iso).slice(0, 5);
}

/** Cabeçalho do extrato: "HOJE · 12 OUT" ou "SEG · 05 OUT". */
export function dayHeader(iso: string, today = new Date()): string {
  const d = fromISODate(iso);
  const mon = MONTHS[d.getMonth()].slice(0, 3).toUpperCase();
  const prefix = iso === toISODate(today) ? "HOJE" : WEEKDAYS[d.getDay()];
  return `${prefix} · ${pad(d.getDate())} ${mon}`;
}
