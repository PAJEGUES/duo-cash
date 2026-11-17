export const CATEGORIES = [
  { key: "ALIMENTACAO", label: "Alimentação", emoji: "🛒", color: "#6D4FC2" },
  { key: "SAUDE", label: "Saúde", emoji: "💊", color: "#E5484D" },
  { key: "TRANSPORTE", label: "Transporte", emoji: "🚗", color: "#3D8BD9" },
  { key: "EDUCACAO", label: "Educação", emoji: "📚", color: "#8E4EC6" },
  { key: "LAZER", label: "Lazer", emoji: "🎉", color: "#F2994A" },
  { key: "INVESTIMENTOS", label: "Investimentos", emoji: "📈", color: "#1FA97A" },
  { key: "DIVIDAS", label: "Dívidas", emoji: "💳", color: "#C2410C" },
  { key: "AGUA_LUZ", label: "Água e Luz", emoji: "💡", color: "#E5B100" },
  { key: "INTERNET_PESSOAL", label: "Internet Pessoal", emoji: "📱", color: "#0EA5E9" },
  { key: "INTERNET_CASA", label: "Internet Casa", emoji: "📶", color: "#0891B2" },
  { key: "TAXA_INCC", label: "Taxa INCC", emoji: "🏗️", color: "#78716C" },
  { key: "TAXA_EVOLUCAO_OBRA", label: "Taxa Evolução de Obra", emoji: "🧱", color: "#A16207" },
  { key: "TAXAS_INESPERADAS", label: "Taxas Inesperadas", emoji: "⚠️", color: "#DC2626" },
  { key: "PET", label: "Zeca (pet)", emoji: "🐶", color: "#B45309" },
  { key: "GASTO_DESNECESSARIO", label: "Gasto Desnecessário", emoji: "🙈", color: "#DB2777" },
  { key: "COMPRAS_ONLINE", label: "Compras Online", emoji: "📦", color: "#4F46E5" },
  { key: "BOLETOS", label: "Boletos", emoji: "🧾", color: "#059669" },
] as const;

export type CategoryKey = (typeof CATEGORIES)[number]["key"];

export const LEISURE_ICONS = [
  { key: "cinema", label: "Cinema", emoji: "🎬" },
  { key: "restaurante", label: "Restaurante", emoji: "🍽️" },
  { key: "bar", label: "Bar", emoji: "🍻" },
  { key: "viagem", label: "Viagem", emoji: "✈️" },
  { key: "show", label: "Show", emoji: "🎤" },
  { key: "jogos", label: "Jogos", emoji: "🎮" },
  { key: "streaming", label: "Streaming", emoji: "📺" },
  { key: "esportes", label: "Esportes", emoji: "⚽" },
  { key: "festa", label: "Festa", emoji: "🥳" },
  { key: "praia", label: "Praia", emoji: "🏖️" },
  { key: "museu", label: "Museu", emoji: "🏛️" },
  { key: "passeio", label: "Passeio", emoji: "🌳" },
] as const;

export type IconKey = (typeof LEISURE_ICONS)[number]["key"];

const byKey = new Map<string, (typeof CATEGORIES)[number]>(CATEGORIES.map((c) => [c.key, c]));
const iconByKey = new Map<string, (typeof LEISURE_ICONS)[number]>(LEISURE_ICONS.map((i) => [i.key, i]));

export function categoryInfo(key: string) {
  return byKey.get(key) ?? { key, label: key, emoji: "💸", color: "#8A8796" };
}

/** Emoji exibido no lançamento: ícone do lazer quando houver, senão o da categoria. */
export function expenseEmoji(category: string, iconKey?: string | null) {
  if (iconKey) {
    const icon = iconByKey.get(iconKey);
    if (icon) return icon.emoji;
  }
  return categoryInfo(category).emoji;
}

export const WORKSPACE_ICONS = ["🏠", "✈️", "🧱", "💑", "🚗", "🎓", "🐶", "🎉", "💼", "🌎"] as const;

export const ROLE_LABEL: Record<string, string> = {
  OWNER: "Dono",
  EDITOR: "Controle total",
  VIEWER: "Somente leitura",
};

/** Cores das pessoas, na ordem em que entraram no ambiente. */
export const PERSON_COLORS = ["#6D4FC2", "#1FA97A", "#F2994A", "#3D8BD9", "#DB2777"] as const;
