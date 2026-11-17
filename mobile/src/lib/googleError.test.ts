import { googleSignInErrorMessage } from "./googleError";

describe("googleSignInErrorMessage", () => {
  it("explica o DEVELOPER_ERROR (10) e mostra o código", () => {
    expect(googleSignInErrorMessage("10")).toBe(
      "O Google não reconheceu este app. Confira o pacote e o SHA-1 do app Android no Firebase. (código 10)",
    );
  });

  it("aceita código numérico", () => {
    expect(googleSignInErrorMessage(12500)).toContain("(código 12500)");
  });

  it("código desconhecido cai na mensagem genérica com o código", () => {
    expect(googleSignInErrorMessage("999")).toBe(
      "Não foi possível entrar com o Google. Confira a conexão e tente de novo. (código 999)",
    );
  });

  it("sem código mostra só a mensagem genérica", () => {
    expect(googleSignInErrorMessage(undefined)).toBe(
      "Não foi possível entrar com o Google. Confira a conexão e tente de novo.",
    );
  });

  it("limita o tamanho do código exibido", () => {
    expect(googleSignInErrorMessage("x".repeat(500)).length).toBeLessThan(150);
  });
});
