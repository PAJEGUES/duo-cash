import { GoogleSignin, isErrorWithCode, isSuccessResponse, statusCodes } from "@react-native-google-signin/google-signin";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { api, ApiError, setSessionExpiredHandler } from "@/api/client";
import { clearTokens, loadSession, saveTokens } from "@/api/storage";
import type { AuthResponse, ServerConfig, User } from "@/api/types";

type AuthState = {
  status: "loading" | "signedOut" | "signedIn";
  user: User | null;
  signInWithGoogle: () => Promise<void>;
  signOut: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<AuthState["status"]>("loading");
  const [user, setUser] = useState<User | null>(null);

  const reset = useCallback(() => {
    setUser(null);
    setStatus("signedOut");
    queryClient.clear();
  }, [queryClient]);

  useEffect(() => {
    setSessionExpiredHandler(reset);
    (async () => {
      const { refresh } = await loadSession();
      if (!refresh) return setStatus("signedOut");
      try {
        setUser(await api<User>("/me"));
        setStatus("signedIn");
      } catch (e) {
        // 401: o cliente já apagou os tokens e avisou (reset). Sem internet ou servidor
        // fora do ar: mantém a sessão e tenta de novo depois.
        if (e instanceof ApiError && e.status === 401) reset();
        else setStatus("signedIn");
      }
    })();
    return () => setSessionExpiredHandler(null);
  }, [reset]);

  const signInWithGoogle = useCallback(async () => {
    // O client id vem do servidor, assim o APK não precisa ser refeito se ele mudar.
    const config = await api<ServerConfig>("/config", { auth: false });
    GoogleSignin.configure({ webClientId: config.google_web_client_id });
    await GoogleSignin.hasPlayServices({ showPlayServicesUpdateDialog: true });
    let idToken: string | null = null;
    try {
      const res = await GoogleSignin.signIn();
      if (!isSuccessResponse(res)) return; // usuário cancelou
      idToken = res.data.idToken;
    } catch (e) {
      if (isErrorWithCode(e) && e.code === statusCodes.IN_PROGRESS) return;
      throw new ApiError(0, "google", "Não foi possível entrar com o Google. Confira a conexão e tente de novo.");
    }
    if (!idToken) throw new ApiError(0, "google", "O Google não devolveu a identificação da conta.");
    const data = await api<AuthResponse>("/auth/google", { method: "POST", body: { id_token: idToken }, auth: false });
    await saveTokens(data.access_token, data.refresh_token);
    setUser(data.user);
    setStatus("signedIn");
  }, []);

  const signOut = useCallback(async () => {
    // Revoga a sessão no servidor (melhor esforço) antes de apagar os tokens do aparelho.
    const { refresh } = await loadSession();
    if (refresh) {
      await api("/auth/logout", { method: "POST", body: { refresh_token: refresh }, auth: false }).catch(() => undefined);
    }
    await clearTokens();
    try {
      await GoogleSignin.signOut();
    } catch {
      // já estava deslogado do Google
    }
    reset();
  }, [reset]);

  const value = useMemo(() => ({ status, user, signInWithGoogle, signOut }), [status, user, signInWithGoogle, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth precisa estar dentro de AuthProvider");
  return ctx;
}
