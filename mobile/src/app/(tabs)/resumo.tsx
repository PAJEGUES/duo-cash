import { router } from "expo-router";
import { useState } from "react";
import { RefreshControl, ScrollView, Text, View } from "react-native";

import { errorMessage } from "@/api/client";
import { useSummary } from "@/api/queries";
import type { Workspace } from "@/api/types";
import { Donut, MonthBars, ProgressBar } from "@/components/Charts";
import { WorkspaceGate } from "@/components/WorkspaceGate";
import { Avatar, Card, ErrorState, FadeIn, Glass, Hero, Loading, Muted, Press, Screen, SectionTitle, T } from "@/components/ui";
import { categoryInfo } from "@/constants/categories";
import { usePalette } from "@/constants/theme";
import { monthLabel, monthShort, shiftMonth, toMonthKey } from "@/lib/dates";
import { formatCents, percent } from "@/lib/money";
import { colorFor, firstName } from "@/lib/people";

const TOP = 5;

function Summary({ ws }: { ws: Workspace }) {
  const p = usePalette();
  const [month, setMonth] = useState(toMonthKey(new Date()));
  const summary = useSummary(ws.id, month);
  const s = summary.data;

  const top = s?.by_category.slice(0, TOP) ?? [];
  const rest = s?.by_category.slice(TOP).reduce((acc, c) => acc + c.total_cents, 0) ?? 0;
  const slices = [
    ...top.map((c) => ({ label: categoryInfo(c.category).label, value: c.total_cents, color: categoryInfo(c.category).color })),
    ...(rest > 0 ? [{ label: "Outras", value: rest, color: p.muted }] : []),
  ];

  return (
    <ScrollView
      contentContainerStyle={{ paddingBottom: 32 }}
      refreshControl={<RefreshControl refreshing={summary.isRefetching} onRefresh={() => void summary.refetch()} tintColor={p.accent} />}
    >
      <Hero>
        <View className="flex-row items-center justify-between">
          <Text className="flex-1 font-bold text-2xl text-white" numberOfLines={1}>{ws.icon} {ws.name}</Text>
          <Press onPress={() => router.push({ pathname: "/ambiente/[id]", params: { id: ws.id } })} accessibilityLabel="Configurações do ambiente">
            <View className="flex-row items-center">
              {ws.members.slice(0, 4).map((m, i) => (
                <View key={m.user_id} style={{ marginLeft: i ? -10 : 0 }}>
                  <Avatar name={m.display_name} color={colorFor(m.user_id, ws.members)} size={34} />
                </View>
              ))}
              <Text className="ml-2 text-lg text-white/80">⚙️</Text>
            </View>
          </Press>
        </View>

        <View className="my-4 flex-row items-center justify-center gap-6">
          <Press onPress={() => setMonth(shiftMonth(month, -1))} accessibilityLabel="Mês anterior"><Text className="px-3 text-2xl text-white">‹</Text></Press>
          <Text className="font-semibold text-base text-white">{monthLabel(month)}</Text>
          <Press onPress={() => setMonth(shiftMonth(month, 1))} accessibilityLabel="Próximo mês"><Text className="px-3 text-2xl text-white">›</Text></Press>
        </View>

        <Glass>
          <Text className="font-medium text-sm text-white/80">Total gasto no mês</Text>
          <Text className="mt-1 font-bold text-4xl text-white">{s ? formatCents(s.total_cents) : "—"}</Text>
        </Glass>
      </Hero>

      <View className="px-4">
        {summary.isPending ? (
          <Loading />
        ) : summary.error ? (
          <ErrorState message={errorMessage(summary.error)} onRetry={summary.refetch} />
        ) : (
          <>
            <SectionTitle>Por categoria</SectionTitle>
            <FadeIn>
              <Card className="flex-row items-center gap-4">
                <Donut slices={slices} center={String(s!.count)} />
                <View className="flex-1 gap-2.5">
                  {slices.length === 0 ? <Muted className="text-sm">Nenhum gasto neste mês.</Muted> : null}
                  {slices.map((sl) => (
                    <View key={sl.label} className="flex-row items-center gap-2">
                      <View style={{ backgroundColor: sl.color }} className="h-2.5 w-2.5 rounded-full" />
                      <T className="flex-1 text-[13px]" numberOfLines={1}>{sl.label}</T>
                      <Muted className="font-semibold text-[13px]">{percent(sl.value, s!.total_cents)}%</Muted>
                    </View>
                  ))}
                </View>
              </Card>
            </FadeIn>

            <SectionTitle>Quem gastou quanto</SectionTitle>
            <FadeIn index={1}>
              <Card className="gap-4">
                {s!.by_author.map((a) => {
                  const color = colorFor(a.user_id, ws.members);
                  return (
                    <View key={a.user_id} className="flex-row items-center gap-3">
                      <Avatar name={a.display_name} color={color} size={36} ring={false} />
                      <View className="flex-1 gap-1.5">
                        <View className="flex-row justify-between">
                          <T className="font-medium">{firstName(a.display_name)}</T>
                          <T className="font-bold">{formatCents(a.total_cents)}</T>
                        </View>
                        <ProgressBar value={percent(a.total_cents, s!.total_cents)} color={color} />
                      </View>
                    </View>
                  );
                })}
              </Card>
            </FadeIn>

            <SectionTitle>Evolução</SectionTitle>
            <FadeIn index={2}>
              <Card>
                <MonthBars
                  data={s!.evolution.map((e) => ({ label: monthShort(e.month), value: e.total_cents, current: e.month === month }))}
                />
              </Card>
            </FadeIn>
          </>
        )}
      </View>
    </ScrollView>
  );
}

export default function ResumoScreen() {
  return (
    <Screen>
      <WorkspaceGate>{(ws) => <Summary ws={ws} />}</WorkspaceGate>
    </Screen>
  );
}
