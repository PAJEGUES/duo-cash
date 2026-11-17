import * as SecureStore from "expo-secure-store";
import Constants from "expo-constants";

// Tokens ficam no cofre do Android (Keystore), nunca em AsyncStorage.
const KEYS = { access: "duocash.access", refresh: "duocash.refresh", server: "duocash.server", workspace: "duocash.workspace" };
const opts: SecureStore.SecureStoreOptions = { keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY };

let cache: { access: string | null; refresh: string | null; server: string | null } | null = null;

export async function loadSession() {
  if (!cache) {
    const [access, refresh, server] = await Promise.all([
      SecureStore.getItemAsync(KEYS.access, opts),
      SecureStore.getItemAsync(KEYS.refresh, opts),
      SecureStore.getItemAsync(KEYS.server, opts),
    ]);
    cache = { access, refresh, server };
  }
  return cache;
}

export async function saveTokens(access: string, refresh: string) {
  const s = await loadSession();
  s.access = access;
  s.refresh = refresh;
  await Promise.all([
    SecureStore.setItemAsync(KEYS.access, access, opts),
    SecureStore.setItemAsync(KEYS.refresh, refresh, opts),
  ]);
}

export async function clearTokens() {
  const s = await loadSession();
  s.access = null;
  s.refresh = null;
  await Promise.all([SecureStore.deleteItemAsync(KEYS.access, opts), SecureStore.deleteItemAsync(KEYS.refresh, opts)]);
}

export function defaultServerUrl(): string {
  return (Constants.expoConfig?.extra?.apiUrl as string | undefined) ?? "";
}

export async function getServerUrl(): Promise<string> {
  const s = await loadSession();
  return s.server || defaultServerUrl();
}

/**
 * Os tokens pertencem ao servidor que os emitiu: trocar de servidor apaga a sessão,
 * assim um token nunca é enviado para outro endereço.
 */
export async function setServerUrl(url: string) {
  const s = await loadSession();
  if (s.server === url) return;
  await clearTokens();
  s.server = url;
  await SecureStore.setItemAsync(KEYS.server, url, opts);
}

/**
 * Segurança: na versão de produção o endereço do servidor só pode ser definido uma vez
 * (quando o APK não veio com um endereço de fábrica). Trocar depois exige limpar os dados
 * do app, o que evita golpes do tipo "o servidor mudou, digite este novo endereço".
 */
export async function canEditServer(): Promise<boolean> {
  if (__DEV__) return true;
  const s = await loadSession();
  return !s.server && !defaultServerUrl();
}

export const getLastWorkspace = () => SecureStore.getItemAsync(KEYS.workspace, opts);
export const setLastWorkspace = (id: string) => SecureStore.setItemAsync(KEYS.workspace, id, opts);
