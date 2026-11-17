import { dayHeader, formatDateBR, fromISODate, monthLabel, monthRange, monthShort, relativeDay, shiftMonth, toISODate, toMonthKey } from "./dates";

const today = new Date(2026, 9, 12); // 12/10/2026 (segunda)

describe("datas", () => {
  it("ISO ida e volta sem problema de fuso", () => expect(toISODate(fromISODate("2026-02-28"))).toBe("2026-02-28"));
  it("chave do mês", () => expect(toMonthKey(today)).toBe("2026-10"));
  it.each([
    ["2026-01", -1, "2025-12"],
    ["2026-12", 1, "2027-01"],
    ["2026-10", 0, "2026-10"],
  ])("shiftMonth(%s, %i) = %s", (m, d, e) => expect(shiftMonth(m, d)).toBe(e));
  it("rótulo do mês", () => expect(monthLabel("2026-10")).toBe("Outubro 2026"));
  it("mês curto", () => expect(monthShort("2026-03")).toBe("Mar"));
  it("fim de fevereiro em ano bissexto", () => expect(monthRange("2028-02")).toEqual({ from: "2028-02-01", to: "2028-02-29" }));
  it("fim de fevereiro em ano comum", () => expect(monthRange("2026-02").to).toBe("2026-02-28"));
  it("formato brasileiro", () => expect(formatDateBR("2026-10-05")).toBe("05/10/2026"));
  it("hoje / ontem / data", () => {
    expect(relativeDay("2026-10-12", today)).toBe("hoje");
    expect(relativeDay("2026-10-11", today)).toBe("ontem");
    expect(relativeDay("2026-10-01", today)).toBe("01/10");
  });
  it("cabeçalho do extrato", () => {
    expect(dayHeader("2026-10-12", today)).toBe("HOJE · 12 OUT");
    expect(dayHeader("2026-10-05", today)).toBe("SEG · 05 OUT");
  });
});
