import { router } from "expo-router";
import { useEffect, useMemo } from "react";
import { RefreshControl, ScrollView, Text, View } from "react-native";

import { errorMessage } from "@/api/client";
import { useExpenses, useWorkspaces } from "@/api/queries";
import type { Workspace } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import { ExpenseRow } from "@/components/ExpenseRow";
import { Avatar, Card, EmptyState, ErrorState, FadeIn, Hero, Loading, Muted, Press, Screen, SectionTitle, T } from "@/components/ui";
import { ROLE_LABEL } from "@/constants/categories";
import { usePalette } from "@/constants/theme";
import { monthLabel, toMonthKey } from "@/lib/dates";
import { useCurrentWorkspace } from "@/lib/currentWorkspace";
import { formatCents } from "@/lib/money";
import { takePendingInvite } from "@/lib/pendingInvite";
import { colorFor, firstName } from "@/lib/people";

function WorkspaceCard({ ws, month, onOpen }: { ws: Workspace; month: string; onOpen: () => void }) {
  const viewer = ws.role === "VIEWER";
  return (
    <Press onPress={onOpen} accessibilityLabel={`Abrir ${ws.name}`}>
      <Card className="mb-3 flex-row items-center gap-3">
        <View className="h-12 w-12 items-center justify-center rounded-2xl bg-accent-soft dark:bg-accent-softDark">
          <Text style={{ fontSize: 24 }}>{ws.icon}</Text>
        </View>
        <View className="flex-1">
          <T className="font-semibold text-base" numberOfLines={1}>{ws.name}</T>
          <View className="mt-1.5 flex-row items-center">
            {ws.members.slice(0, 4).map((m, i) => (
              <View key={m.user_id} style={{ marginLeft: i ? -8 : 0 }}>
                <Avatar name={m.display_name} color={colorFor(m.user_id, ws.members)} size={24} />
              </View>
            ))}
            <View className={`ml-2 rounded-full px-2 py-0.5 ${viewer ? "bg-paper dark:bg-night-line" : "bg-partner-soft dark:bg-partner-softDark"}`}>
              <Text className={`font-semibold text-[11px] ${viewer ? "text-ink-muted dark:text-night-muted" : "text-partner"}`}>{ROLE_LABEL[ws.role]}</Text>
            </View>
          </View>
        </View>
        <View className="items-end">
          <T className="font-bold text-base">{formatCents(ws.month_total_cents)}</T>
          <Muted className="text-[11px]">em {monthLabel(month).split(" ")[0].toLowerCase()}</Muted>
        </View>
      </Card>
    </Press>
  );
}

export default function Home() {
  const { user } = useAuth();
  const p = usePalette();
  const month = toMonthKey(new Date());
  const { workspaceId, select } = useCurrentWorkspace();
  const workspaces = useWorkspaces(month);

  const active = useMemo(() => workspaces.data?.filter((w) => !w.archived_at) ?? [], [workspaces.data]);
  const archived = useMemo(() => workspaces.data?.filter((w) => w.archived_at) ?? [], [workspaces.data]);
  const current = useMemo(
    () => workspaces.data?.find((w) => w.id === workspaceId) ?? active[0],
    [workspaces.data, workspaceId, active],
  );
  const recent = useExpenses(current?.id, {});

  // Se o ambiente salvo sumiu (removido/excluído), passa a usar o primeiro.
  useEffect(() => {
    if (current && current.id !== workspaceId) select(current.id);
  }, [current, workspaceId, select]);

  // Convite aberto antes do login.
  useEffect(() => {
    const token = takePendingInvite();
    if (token) router.push({ pathname: "/join/[token]", params: { token } });
  }, []);

  const open = (ws: Workspace) => {
    select(ws.id);
    router.navigate("/resumo");
  };

  const latest = recent.data?.pages[0]?.items.slice(0, 5) ?? [];

  return (
    <Screen>
      <ScrollView
        contentContainerStyle={{ paddingBottom: 32 }}
        refreshControl={<RefreshControl refreshing={workspaces.isRefetching} onRefresh={() => { workspaces.refetch(); recent.refetch(); }} tintColor={p.accent} />}
      >
        <Hero>
          <View className="flex-row items-center justify-between">
            <View>
              <Text className="font-sans text-sm text-white/75">Olá, {firstName(user?.display_name ?? "")} 👋</Text>
              <Text className="mt-1 font-bold text-2xl text-white">Seus ambientes</Text>
            </View>
            <Press onPress={() => router.push("/conta")} accessibilityLabel="Minha conta">
              <Avatar name={user?.display_name ?? "?"} color={p.accent} size={42} />
            </Press>
          </View>
        </Hero>

        <View className="px-4 pt-5">
          {workspaces.isPending ? (
            <Loading />
          ) : workspaces.error ? (
            <ErrorState message={errorMessage(workspaces.error)} onRetry={workspaces.refetch} />
          ) : (
            <>
              {active.length === 0 ? (
                <EmptyState emoji="💑" title="Crie seu primeiro ambiente" text="Um ambiente é onde vocês lançam os gastos juntos, como “Casa” ou “Viagem”." />
              ) : (
                active.map((ws, i) => (
                  <FadeIn key={ws.id} index={i}>
                    <WorkspaceCard ws={ws} month={month} onOpen={() => open(ws)} />
                  </FadeIn>
                ))
              )}

              <Press onPress={() => router.push("/ambiente/novo")} accessibilityLabel="Criar novo ambiente">
                <View className="items-center rounded-2xl border-2 border-dashed border-accent/40 py-4">
                  <Text className="font-semibold text-accent dark:text-white">+ Criar novo ambiente</Text>
                </View>
              </Press>

              <Press onPress={() => router.push("/scan")} accessibilityLabel="Entrar com convite">
                <Text className="mt-4 text-center font-medium text-sm text-accent dark:text-white">📷 Recebi um convite</Text>
              </Press>

              {archived.length > 0 ? (
                <>
                  <SectionTitle>Arquivados</SectionTitle>
                  <View className="opacity-60">
                    {archived.map((ws) => (
                      <WorkspaceCard key={ws.id} ws={ws} month={month} onOpen={() => router.push({ pathname: "/ambiente/[id]", params: { id: ws.id } })} />
                    ))}
                  </View>
                </>
              ) : null}

              {current ? (
                <>
                  <SectionTitle right={<Muted className="text-xs">{current.icon} {current.name}</Muted>}>Últimos lançamentos</SectionTitle>
                  <Card className="py-1">
                    {recent.isPending ? (
                      <Loading />
                    ) : latest.length === 0 ? (
                      <Muted className="py-6 text-center text-sm">Nenhum gasto ainda. Toque no + para lançar.</Muted>
                    ) : (
                      latest.map((e) => (
                        <ExpenseRow
                          key={e.id}
                          expense={e}
                          members={current.members}
                          onPress={current.role !== "VIEWER" ? () => router.push({ pathname: "/gasto", params: { id: e.id } }) : undefined}
                        />
                      ))
                    )}
                  </Card>
                </>
              ) : null}
            </>
          )}
        </View>
      </ScrollView>
    </Screen>
  );
}
