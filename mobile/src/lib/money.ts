export const MAX_AMOUNT_CENTS = 10_000_000_000;

const formatter = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

/** 123456 -> "R$ 1.234,56" (troca o espaço não separável por espaço comum). */
export function formatCents(cents: number): string {
  return formatter.format(cents / 100).replace(/ /g, " ");
}

/** "R$ 1.234,56" sem o prefixo, para o campo de valor. */
export function formatCentsPlain(cents: number): string {
  return formatCents(cents).replace(/^-?R\$\s?/, "");
}

/**
 * Converte o que o usuário digitou no teclado numérico em centavos.
 * O campo funciona como caixa registradora: cada dígito empurra os anteriores.
 * "8600" -> 8600 (R$ 86,00). Ignora tudo que não for dígito.
 */
export function digitsToCents(input: string): number {
  const digits = input.replace(/\D/g, "").replace(/^0+/, "").slice(0, 11);
  if (!digits) return 0;
  return Math.min(Number.parseInt(digits, 10), MAX_AMOUNT_CENTS);
}

/** Converte texto com vírgula ("12,5" / "1.234,56") em centavos; null se inválido. */
export function parseBRL(input: string): number | null {
  const clean = input.trim().replace(/^R\$\s?/, "").replace(/\./g, "").replace(",", ".");
  if (!/^\d+(\.\d{0,2})?$/.test(clean)) return null;
  const [int, dec = ""] = clean.split(".");
  const cents = Number.parseInt(int, 10) * 100 + Number.parseInt((dec + "00").slice(0, 2), 10);
  return cents <= MAX_AMOUNT_CENTS ? cents : null;
}

export function percent(part: number, total: number): number {
  if (total <= 0) return 0;
  return Math.round((part / total) * 100);
}
