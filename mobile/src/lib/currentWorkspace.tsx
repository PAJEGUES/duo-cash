import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

import { getLastWorkspace, setLastWorkspace } from "@/api/storage";

type Ctx = { workspaceId: string | null; ready: boolean; select: (id: string) => void };
const CurrentWorkspaceContext = createContext<Ctx | null>(null);

/** Lembra o último ambiente aberto, usado pelas abas Extrato, Resumo e Convidar e pelo botão +. */
export function CurrentWorkspaceProvider({ children }: { children: ReactNode }) {
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    getLastWorkspace()
      .then(setWorkspaceId)
      .finally(() => setReady(true));
  }, []);

  const select = useCallback((id: string) => {
    setWorkspaceId(id);
    setLastWorkspace(id).catch(() => undefined);
  }, []);

  const value = useMemo(() => ({ workspaceId, ready, select }), [workspaceId, ready, select]);
  return <CurrentWorkspaceContext.Provider value={value}>{children}</CurrentWorkspaceContext.Provider>;
}

export function useCurrentWorkspace() {
  const ctx = useContext(CurrentWorkspaceContext);
  if (!ctx) throw new Error("useCurrentWorkspace precisa do provider");
  return ctx;
}
