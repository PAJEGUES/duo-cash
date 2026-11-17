import { normalizeServerUrl, parseInviteToken, validateExpense, validateWorkspaceName, type ExpenseInput } from "./validation";

const today = new Date(2026, 9, 12);
const base: ExpenseInput = { amount_cents: 8600, spent_at: "2026-10-12", description: "Cinema + pipoca", category: "LAZER", icon_key: "cinema" };

describe("validateExpense", () => {
  it("aceita um gasto válido", () => expect(validateExpense(base, today)).toEqual({}));

  it.each([0, -1, 1.5, Number.NaN, 10_000_000_001])("rejeita valor %p", (amount_cents) =>
    expect(validateExpense({ ...base, amount_cents }, today).amount_cents).toBeDefined(),
  );
  it.each([1, 10_000_000_000])("aceita valor limite %p", (amount_cents) =>
    expect(validateExpense({ ...base, amount_cents }, today).amount_cents).toBeUndefined(),
  );

  it("descrição com exatamente 100 caracteres passa", () =>
    expect(validateExpense({ ...base, description: "a".repeat(100) }, today).description).toBeUndefined());
  it("descrição com 101 caracteres falha", () =>
    expect(validateExpense({ ...base, description: "a".repeat(101) }, today).description).toBeDefined());
  it("emoji conta como 1 caractere", () =>
    expect(validateExpense({ ...base, description: "🎬".repeat(100) }, today).description).toBeUndefined());
  it.each(["", "   ", "\n\t"])("descrição vazia %p falha", (description) =>
    expect(validateExpense({ ...base, description }, today).description).toBeDefined());

  it.each(["2026-13-01", "2026-02-30", "12/10/2026", "", "2026-1-1", "1999-12-31", "2026-11-13"])("rejeita data %p", (spent_at) =>
    expect(validateExpense({ ...base, spent_at }, today).spent_at).toBeDefined(),
  );
  it.each(["2000-01-01", "2026-10-12", "2026-11-12"])("aceita data %p (retroativa ou até 31 dias)", (spent_at) =>
    expect(validateExpense({ ...base, spent_at }, today).spent_at).toBeUndefined(),
  );

  it.each(["", "lazer", "OUTRA", "Lazer"])("rejeita categoria %p", (category) =>
    expect(validateExpense({ ...base, category }, today).category).toBeDefined());
  it("rejeita ícone desconhecido", () => expect(validateExpense({ ...base, icon_key: "hack" }, today).icon_key).toBeDefined());
  it("ícone é opcional", () => expect(validateExpense({ ...base, icon_key: null }, today)).toEqual({}));
});

describe("validateWorkspaceName", () => {
  it.each(["", "  "])("vazio %p falha", (n) => expect(validateWorkspaceName(n)).not.toBeNull());
  it("61 caracteres falha", () => expect(validateWorkspaceName("a".repeat(61))).not.toBeNull());
  it("nome normal passa", () => expect(validateWorkspaceName("Viagem Chile 2026")).toBeNull());
});

describe("parseInviteToken", () => {
  const token = "AbCdEf0123456789_-xyzAbCdEf012345";
  it("lê o link do app", () => expect(parseInviteToken(`duocash://join/${token}`)).toBe(token));
  it("lê o link https", () => expect(parseInviteToken(`https://1-2-3-4.sslip.io/convite/${token}`)).toBe(token));
  it.each([
    "https://evil.com/other/abc",
    `http://x.com/convite/${token}`,
    `duocash://join/${token}?x=1`,
    "duocash://join/curto",
    `duocash://join/${token}/../../x`,
    `javascript:alert(1)//duocash://join/${token}`,
    "",
  ])("ignora %p", (data) => expect(parseInviteToken(data)).toBeNull());
});

describe("normalizeServerUrl", () => {
  it("aceita https e remove a barra final", () => expect(normalizeServerUrl("https://API.Exemplo.com/")).toBe("https://api.exemplo.com"));
  it("aceita porta", () => expect(normalizeServerUrl("https://a.b:8443")).toBe("https://a.b:8443"));
  it("bloqueia http em produção", () => expect(normalizeServerUrl("http://a.b")).toBeNull());
  it("permite http só em desenvolvimento", () => expect(normalizeServerUrl("http://192.168.0.10:8000", true)).toBe("http://192.168.0.10:8000"));
  it.each(["javascript:alert(1)", "https://a.b/path", "https://user@a.b", "ftp://a.b", "a.b", ""])("rejeita %p", (u) =>
    expect(normalizeServerUrl(u)).toBeNull(),
  );
});
