import { categoryInfo, CATEGORIES, expenseEmoji, LEISURE_ICONS, PERSON_COLORS } from "@/constants/categories";
import { colorFor, firstName, initial } from "./people";

describe("pessoas", () => {
  const members = [{ user_id: "a" }, { user_id: "b" }];
  it("dono é roxo e parceiro(a) verde", () => {
    expect(colorFor("a", members)).toBe(PERSON_COLORS[0]);
    expect(colorFor("b", members)).toBe(PERSON_COLORS[1]);
  });
  it("ex-membro recebe uma cor estável", () => expect(colorFor("z", members)).toBe(PERSON_COLORS[2]));
  it("inicial e primeiro nome", () => {
    expect(initial("  lucas silva")).toBe("L");
    expect(initial("")).toBe("?");
    expect(firstName("Bia Souza")).toBe("Bia");
  });
});

describe("categorias", () => {
  it("são exatamente 17, sem chave repetida", () => {
    expect(CATEGORIES).toHaveLength(17);
    expect(new Set(CATEGORIES.map((c) => c.key)).size).toBe(17);
  });
  it("ícones de lazer sem repetição", () => expect(new Set(LEISURE_ICONS.map((i) => i.key)).size).toBe(LEISURE_ICONS.length));
  it("emoji do ícone tem prioridade", () => expect(expenseEmoji("LAZER", "cinema")).toBe("🎬"));
  it("cai para o emoji da categoria", () => expect(expenseEmoji("ALIMENTACAO", null)).toBe("🛒"));
  it("categoria desconhecida não quebra a tela", () => expect(categoryInfo("XYZ").label).toBe("XYZ"));
});
