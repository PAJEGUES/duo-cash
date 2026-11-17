import { router } from "expo-router";
import { useEffect, useMemo, useState } from "react";
import { ActivityIndicator, RefreshControl, SectionList, Text, TextInput, View } from "react-native";

import { errorMessage } from "@/api/client";
import { useExpenses } from "@/api/queries";
import type { Expense, ExpenseFilters, Workspace } from "@/api/types";
import { ExpenseRow } from "@/components/ExpenseRow";
import { WorkspaceGate } from "@/components/WorkspaceGate";
import { Card, Chip, EmptyState, ErrorState, Hero, Loading, Muted, Press, Screen, T } from "@/components/ui";
import { CATEGORIES } from "@/constants/categories";
import { usePalette } from "@/constants/theme";
import { dayHeader, monthLabel, monthRange, shiftMonth, toMonthKey } from "@/lib/dates";
import { formatCents, parseBRL } from "@/lib/money";
import { firstName } from "@/lib/people";

type Panel = null | "category" | "author" | "amount";

function useDebounced<T>(value: T, ms = 350) {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return v;
}

function AmountInput({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  const p = usePalette();
  return (
    <View className="flex-1">
      <Muted className="mb-1 text-xs">{label}</Muted>
      <TextInput
        value={value}
        onChangeText={(t) => onChange(t.replace(/[^\d,.]/g, "").slice(0, 14))}
        keyboardType="decimal-pad"
        placeholder="0,00"
        placeholderTextColor={p.muted}
        className="rounded-xl border border-paper-line px-3 py-2.5 font-sans text-base text-ink dark:border-night-line dark:text-white"
      />
    </View>
  );
}

function Statement({ ws }: { ws: Workspace }) {
  const p = usePalette();
  const [q, setQ] = useState("");
  const [month, setMonth] = useState<string | null>(toMonthKey(new Date()));
  const [categories, setCategories] = useState<string[]>([]);
  const [authorId, setAuthorId] = useState<string | undefined>();
  const [minText, setMinText] = useState("");
  const [maxText, setMaxText] = useState("");
  const [panel, setPanel] = useState<Panel>(null);
  const debouncedQ = useDebounced(q.trim());
  const amountMin = parseBRL(minText) ?? undefined;
  const amountMax = parseBRL(maxText) ?? undefined;

  const filters: ExpenseFilters = useMemo(
    () => ({
      q: debouncedQ || undefined,
      category: categories.length ? categories : undefined,
      author_id: authorId,
      ...(month ? { date_from: monthRange(month).from, date_to: monthRange(month).to } : {}),
      amount_min: amountMin,
      amount_max: amountMax,
    }),
    [debouncedQ, categories, authorId, month, amountMin, amountMax],
  );

  const list = useExpenses(ws.id, filters);
  const items = useMemo(() => list.data?.pages.flatMap((pg) => pg.items) ?? [], [list.data]);
  const first = list.data?.pages[0];

  const sections = useMemo(() => {
    const map = new Map<string, Expense[]>();
    for (const e of items) map.set(e.spent_at, [...(map.get(e.spent_at) ?? []), e]);
    return [...map.entries()].map(([day, data]) => ({ title: dayHeader(day), data }));
  }, [items]);

  const toggleCat = (k: string) => setCategories((c) => (c.includes(k) ? c.filter((x) => x !== k) : [...c, k]));
  const author = ws.members.find((m) => m.user_id === authorId);

  return (
    <SectionList
      sections={sections}
      keyExtractor={(e) => e.id}
      stickySectionHeadersEnabled={false}
      onEndReached={() => list.hasNextPage && !list.isFetchingNextPage && list.fetchNextPage()}
      onEndReachedThreshold={0.4}
      refreshControl={<RefreshControl refreshing={list.isRefetching && !list.isFetchingNextPage} onRefresh={() => void list.refetch()} tintColor={p.accent} />}
      contentContainerStyle={{ paddingBottom: 32 }}
      ListHeaderComponent={
        <>
          <Hero>
            <View className="flex-row items-end justify-between">
              <Text className="font-bold text-2xl text-white">Extrato</Text>
              <Text className="font-medium text-sm text-white/75">{ws.icon} {ws.name}</Text>
            </View>
            <View className="mt-4 flex-row items-center rounded-2xl border border-white/20 bg-white/15 px-4">
              <Text className="text-white/80">🔎</Text>
              <TextInput
                value={q}
                onChangeText={(t) => setQ(t.slice(0, 100))}
                placeholder="Buscar por descrição"
                placeholderTextColor="rgba(255,255,255,0.6)"
                className="flex-1 px-3 py-3 font-sans text-base text-white"
                returnKeyType="search"
              />
              {q ? <Press onPress={() => setQ("")} haptic={false} accessibilityLabel="Limpar busca"><Text className="text-white/80">✕</Text></Press> : null}
            </View>
          </Hero>

          <View className="px-4 pt-4">
            <View className="flex-row flex-wrap gap-2">
              <Chip label={month ? `‹ ${monthLabel(month)} ›` : "📅 Todos os meses"} active={!!month} onPress={() => setMonth(month ? null : toMonthKey(new Date()))} />
              <Chip label={categories.length ? `🏷️ ${categories.length} categoria(s)` : "🏷️ Categoria"} active={categories.length > 0} onPress={() => setPanel(panel === "category" ? null : "category")} />
              <Chip label={author ? `👤 ${firstName(author.display_name)}` : "👤 Autor"} active={!!author} onPress={() => setPanel(panel === "author" ? null : "author")} />
              <Chip label={amountMin || amountMax ? "💲 Valor ✓" : "💲 Valor"} active={!!(amountMin || amountMax)} onPress={() => setPanel(panel === "amount" ? null : "amount")} />
            </View>

            {month ? (
              <View className="mt-3 flex-row justify-center gap-6">
                <Press onPress={() => setMonth(shiftMonth(month, -1))} accessibilityLabel="Mês anterior"><Text className="font-semibold text-accent dark:text-white">‹ anterior</Text></Press>
                <Press onPress={() => setMonth(shiftMonth(month, 1))} accessibilityLabel="Próximo mês"><Text className="font-semibold text-accent dark:text-white">próximo ›</Text></Press>
              </View>
            ) : null}

            {panel === "category" ? (
              <Card className="mt-3 flex-row flex-wrap gap-2">
                {CATEGORIES.map((c) => (
                  <Chip key={c.key} label={`${c.emoji} ${c.label}`} active={categories.includes(c.key)} onPress={() => toggleCat(c.key)} />
                ))}
              </Card>
            ) : null}
            {panel === "author" ? (
              <Card className="mt-3 flex-row flex-wrap gap-2">
                <Chip label="Todos" active={!authorId} onPress={() => setAuthorId(undefined)} />
                {ws.members.map((m) => (
                  <Chip key={m.user_id} label={firstName(m.display_name)} active={authorId === m.user_id} onPress={() => setAuthorId(m.user_id)} />
                ))}
              </Card>
            ) : null}
            {panel === "amount" ? (
              <Card className="mt-3 flex-row gap-3">
                <AmountInput label="De (R$)" value={minText} onChange={setMinText} />
                <AmountInput label="Até (R$)" value={maxText} onChange={setMaxText} />
              </Card>
            ) : null}

            {first ? (
              <View className="mt-4 flex-row items-center justify-between rounded-2xl bg-accent-soft px-4 py-3 dark:bg-accent-softDark">
                <T className="text-sm">{first.total_count} lançamento(s)</T>
                <T className="font-bold text-base">{formatCents(first.total_cents)}</T>
              </View>
            ) : null}
          </View>
        </>
      }
      renderSectionHeader={({ section }) => (
        <Muted className="mx-5 mb-2 mt-5 font-semibold text-xs tracking-widest">{section.title}</Muted>
      )}
      renderItem={({ item, index, section }) => (
        <View
          className={`mx-4 border-x border-paper-line bg-paper-card px-4 dark:border-night-line dark:bg-night-card ${
            index === 0 ? "rounded-t-2xl border-t" : ""
          } ${index === section.data.length - 1 ? "rounded-b-2xl border-b" : ""}`}
        >
          <ExpenseRow
            expense={item}
            members={ws.members}
            showDate={false}
            onPress={ws.role !== "VIEWER" ? () => router.push({ pathname: "/gasto", params: { id: item.id } }) : undefined}
          />
        </View>
      )}
      ListEmptyComponent={
        list.isPending ? (
          <Loading />
        ) : list.error ? (
          <ErrorState message={errorMessage(list.error)} onRetry={list.refetch} />
        ) : (
          <EmptyState emoji="🧾" title="Nada encontrado" text="Tente outro termo ou remova algum filtro." />
        )
      }
      ListFooterComponent={list.isFetchingNextPage ? <ActivityIndicator className="my-6" color={p.accent} /> : undefined}
    />
  );
}

export default function ExtratoScreen() {
  return (
    <Screen>
      <WorkspaceGate>{(ws) => <Statement ws={ws} />}</WorkspaceGate>
    </Screen>
  );
}
