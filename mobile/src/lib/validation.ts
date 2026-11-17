import { CATEGORIES, LEISURE_ICONS } from "@/constants/categories";
import { MAX_AMOUNT_CENTS } from "./money";
import { fromISODate, toISODate } from "./dates";

export const DESCRIPTION_MAX = 100;
export const WORKSPACE_NAME_MAX = 60;
const MAX_FUTURE_DAYS = 31;

export type ExpenseInput = {
  amount_cents: number;
  spent_at: string;
  description: string;
  category: string;
  icon_key?: string | null;
};

export type FieldErrors = Partial<Record<keyof ExpenseInput, string>>;

/** Mesmas regras da API (docs/requisitos.md); o servidor confere de novo. */
export function validateExpense(input: ExpenseInput, today = new Date()): FieldErrors {
  const errors: FieldErrors = {};
  if (!Number.isInteger(input.amount_cents) || input.amount_cents <= 0) {
    errors.amount_cents = "Informe um valor maior que zero.";
  } else if (input.amount_cents > MAX_AMOUNT_CENTS) {
    errors.amount_cents = "Valor muito alto.";
  }

  const desc = input.description.trim();
  if (!desc) errors.description = "Escreva uma descrição.";
  else if ([...desc].length > DESCRIPTION_MAX) errors.description = `Máximo de ${DESCRIPTION_MAX} caracteres.`;

  if (!/^\d{4}-\d{2}-\d{2}$/.test(input.spent_at) || toISODate(fromISODate(input.spent_at)) !== input.spent_at) {
    errors.spent_at = "Data inválida.";
  } else {
    const limit = new Date(today);
    limit.setDate(limit.getDate() + MAX_FUTURE_DAYS);
    if (input.spent_at < "2000-01-01") errors.spent_at = "Data muito antiga.";
    else if (input.spent_at > toISODate(limit)) errors.spent_at = "Data muito distante no futuro.";
  }

  if (!CATEGORIES.some((c) => c.key === input.category)) errors.category = "Escolha uma categoria.";
  if (input.icon_key && !LEISURE_ICONS.some((i) => i.key === input.icon_key)) errors.icon_key = "Ícone inválido.";
  return errors;
}

export function validateWorkspaceName(name: string): string | null {
  const n = name.trim();
  if (!n) return "Dê um nome ao ambiente.";
  if ([...n].length > WORKSPACE_NAME_MAX) return `Máximo de ${WORKSPACE_NAME_MAX} caracteres.`;
  return null;
}

/**
 * Extrai o token do convite de um QR Code ou link.
 * Aceita "duocash://join/<token>" e "https://<servidor>/convite/<token>".
 */
export function parseInviteToken(data: string): string | null {
  const m = data.trim().match(/^(?:duocash:\/\/join\/|https:\/\/[^/\s]+\/convite\/)([A-Za-z0-9_-]{16,128})\/?$/);
  return m ? m[1] : null;
}

/** Só aceita https (http apenas para rede local durante o desenvolvimento). */
export function normalizeServerUrl(input: string, allowHttp = false): string | null {
  const url = input.trim().replace(/\/+$/, "");
  const re = allowHttp ? /^https?:\/\/[A-Za-z0-9.-]+(:\d{1,5})?$/ : /^https:\/\/[A-Za-z0-9.-]+(:\d{1,5})?$/;
  return re.test(url) ? url.toLowerCase() : null;
}
