const mockStore = new Map<string, string>();
jest.mock("expo-secure-store", () => ({
  WHEN_UNLOCKED_THIS_DEVICE_ONLY: 1,
  getItemAsync: jest.fn(async (k: string) => mockStore.get(k) ?? null),
  setItemAsync: jest.fn(async (k: string, v: string) => void mockStore.set(k, v)),
  deleteItemAsync: jest.fn(async (k: string) => void mockStore.delete(k)),
}));
jest.mock("expo-constants", () => ({ expoConfig: { extra: { apiUrl: "https://api.test" } } }));

type Reply = { status: number; body?: unknown };
const json = (r: Reply) =>
  ({ ok: r.status >= 200 && r.status < 300, status: r.status, json: async () => r.body }) as unknown as Response;

let api: typeof import("./client").api;
let ApiError: typeof import("./client").ApiError;
let setSessionExpiredHandler: typeof import("./client").setSessionExpiredHandler;
let fetchMock: jest.Mock;

beforeEach(() => {
  jest.resetModules();
  mockStore.clear();
  mockStore.set("duocash.access", "old-access");
  mockStore.set("duocash.refresh", "refresh-1");
  fetchMock = jest.fn();
  globalThis.fetch = fetchMock;
  // eslint-disable-next-line @typescript-eslint/no-require-imports -- módulo recarregado a cada teste (jest.resetModules)
  ({ api, ApiError, setSessionExpiredHandler } = require("./client"));
});

describe("cliente da API", () => {
  it("envia o token e usa a URL padrão", async () => {
    fetchMock.mockResolvedValueOnce(json({ status: 200, body: { ok: 1 } }));
    await expect(api("/me")).resolves.toEqual({ ok: 1 });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("https://api.test/api/v1/me");
    expect(init.headers.Authorization).toBe("Bearer old-access");
  });

  it("renova o token expirado uma vez e repete a chamada", async () => {
    fetchMock
      .mockResolvedValueOnce(json({ status: 401, body: { error: { code: "token_expired", message: "x" } } }))
      .mockResolvedValueOnce(json({ status: 200, body: { access_token: "new-access", refresh_token: "refresh-2", user: {} } }))
      .mockResolvedValueOnce(json({ status: 200, body: { ok: 2 } }));
    await expect(api("/me")).resolves.toEqual({ ok: 2 });
    expect(fetchMock.mock.calls[2][1].headers.Authorization).toBe("Bearer new-access");
    expect(mockStore.get("duocash.refresh")).toBe("refresh-2");
  });

  it("várias chamadas simultâneas fazem só UMA renovação", async () => {
    let refreshes = 0;
    fetchMock.mockImplementation(async (url: string, init: RequestInit) => {
      if (url.endsWith("/auth/refresh")) {
        refreshes++;
        return json({ status: 200, body: { access_token: "new", refresh_token: "r2", user: {} } });
      }
      const auth = (init.headers as Record<string, string>).Authorization;
      return auth === "Bearer new" ? json({ status: 200, body: {} }) : json({ status: 401, body: { error: { code: "token_expired", message: "x" } } });
    });
    await Promise.all([api("/a"), api("/b"), api("/c"), api("/d")]);
    expect(refreshes).toBe(1);
  });

  it("sessão inválida apaga os tokens e avisa o app", async () => {
    const expired = jest.fn();
    setSessionExpiredHandler(expired);
    fetchMock
      .mockResolvedValueOnce(json({ status: 401, body: { error: { code: "unauthorized", message: "x" } } }))
      .mockResolvedValueOnce(json({ status: 401, body: { error: { code: "unauthorized", message: "x" } } }));
    await expect(api("/me")).rejects.toMatchObject({ status: 401 });
    expect(expired).toHaveBeenCalled();
    expect(mockStore.has("duocash.refresh")).toBe(false);
  });

  it("traduz o erro padrão da API com campos", async () => {
    fetchMock.mockResolvedValueOnce(
      json({ status: 400, body: { error: { code: "validation", message: "Dados inválidos", fields: { amount_cents: "x" } } } }),
    );
    const err = (await api("/x", { method: "POST", body: {} }).catch((e: unknown) => e)) as InstanceType<typeof ApiError>;
    expect(err).toBeInstanceOf(ApiError);
    expect(err.fields).toEqual({ amount_cents: "x" });
  });

  it("não mostra detalhes internos quando o corpo não é JSON", async () => {
    fetchMock.mockResolvedValueOnce({ ok: false, status: 500, json: async () => { throw new Error("<html>stack</html>"); } });
    await expect(api("/x")).rejects.toMatchObject({ message: "Algo deu errado no servidor. Tente de novo." });
  });

  it("falha de rede vira erro amigável com status 0", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("Network request failed"));
    await expect(api("/x")).rejects.toMatchObject({ status: 0, code: "network" });
  });

  it("204 devolve undefined", async () => {
    fetchMock.mockResolvedValueOnce({ ok: true, status: 204, json: async () => { throw new Error("vazio"); } });
    await expect(api("/x", { method: "DELETE" })).resolves.toBeUndefined();
  });

  it("chamadas públicas não enviam token", async () => {
    fetchMock.mockResolvedValueOnce(json({ status: 200, body: {} }));
    await api("/config", { auth: false });
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBeUndefined();
  });
});

describe("servidor", () => {
  it("trocar de servidor apaga a sessão (token nunca vai para outro endereço)", async () => {
    const storage = require("./storage"); // eslint-disable-line @typescript-eslint/no-require-imports
    await storage.setServerUrl("https://outro.servidor");
    expect(mockStore.has("duocash.access")).toBe(false);
    expect(mockStore.has("duocash.refresh")).toBe(false);
    fetchMock.mockResolvedValueOnce(json({ status: 200, body: {} }));
    await api("/config", { auth: false });
    expect(fetchMock.mock.calls[0][0]).toBe("https://outro.servidor/api/v1/config");
  });

  it("salvar o mesmo servidor mantém a sessão", async () => {
    const storage = require("./storage"); // eslint-disable-line @typescript-eslint/no-require-imports
    await storage.setServerUrl("https://api.test");
    await storage.setServerUrl("https://api.test");
    expect(mockStore.has("duocash.refresh")).toBe(false); // 1ª troca (padrão -> salvo) limpou
    await storage.saveTokens("a", "r");
    await storage.setServerUrl("https://api.test");
    expect(mockStore.get("duocash.refresh")).toBe("r");
  });
});
