import { digitsToCents, formatCents, formatCentsPlain, MAX_AMOUNT_CENTS, parseBRL, percent } from "./money";

describe("formatCents", () => {
  it.each([
    [0, "R$ 0,00"],
    [1, "R$ 0,01"],
    [8600, "R$ 86,00"],
    [123456, "R$ 1.234,56"],
    [100000000, "R$ 1.000.000,00"],
  ])("%i -> %s", (cents, expected) => expect(formatCents(cents)).toBe(expected));

  it("sem prefixo para o campo de valor", () => expect(formatCentsPlain(31275)).toBe("312,75"));
});

describe("digitsToCents (teclado tipo caixa registradora)", () => {
  it.each([
    ["", 0],
    ["0", 0],
    ["8", 8],
    ["86", 86],
    ["8600", 8600],
    ["86,00", 8600],
    ["R$ 1.234,56", 123456],
    ["abc", 0],
    ["000123", 123],
  ])("%p -> %i", (input, expected) => expect(digitsToCents(input)).toBe(expected));

  it("nunca passa do limite", () => expect(digitsToCents("9".repeat(30))).toBeLessThanOrEqual(MAX_AMOUNT_CENTS));
  it("sempre devolve inteiro (sem float)", () => expect(Number.isInteger(digitsToCents("12345"))).toBe(true));
});

describe("parseBRL", () => {
  it.each([
    ["12", 1200],
    ["12,5", 1250],
    ["12,50", 1250],
    ["1.234,56", 123456],
    ["R$ 0,01", 1],
    ["0,1", 10],
  ])("%p -> %i", (input, expected) => expect(parseBRL(input)).toBe(expected));

  it.each(["", "abc", "1,234", "-5", "12,345", "1e5", "NaN"])("%p é inválido", (input) => expect(parseBRL(input)).toBeNull());

  it("evita erro de arredondamento de float", () => expect(parseBRL("0,29")).toBe(29));
  it("rejeita acima do limite", () => expect(parseBRL("999999999999")).toBeNull());
});

describe("percent", () => {
  it("divide sem quebrar com total zero", () => expect(percent(10, 0)).toBe(0));
  it("arredonda", () => expect(percent(1, 3)).toBe(33));
});
