import { router } from "expo-router";
import type { ReactNode } from "react";

import { useWorkspace } from "@/api/queries";
import type { Workspace } from "@/api/types";
import { errorMessage } from "@/api/client";
import { useCurrentWorkspace } from "@/lib/currentWorkspace";
import { Button, EmptyState, ErrorState, Loading, Screen } from "./ui";

/** Telas que dependem do ambiente selecionado (Extrato, Resumo, Convidar). */
export function WorkspaceGate({ children }: { children: (ws: Workspace) => ReactNode }) {
  const { workspaceId, ready } = useCurrentWorkspace();
  const q = useWorkspace(workspaceId ?? undefined);

  if (!ready || (workspaceId && q.isPending)) return <Screen><Loading /></Screen>;
  if (!workspaceId || (q.error && "status" in q.error && q.error.status === 404)) {
    return (
      <Screen className="justify-center">
        <EmptyState
          emoji="🏠"
          title="Escolha um ambiente"
          text="Abra um ambiente na tela Início para ver o extrato, o resumo e os convites."
          action={<Button title="Ir para Início" variant="ghost" onPress={() => router.navigate("/")} />}
        />
      </Screen>
    );
  }
  if (q.error) return <Screen className="justify-center"><ErrorState message={errorMessage(q.error)} onRetry={q.refetch} /></Screen>;
  return <>{children(q.data!)}</>;
}
