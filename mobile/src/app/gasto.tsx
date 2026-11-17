import DateTimePicker from "@react-native-community/datetimepicker";
import { useQueryClient, type InfiniteData } from "@tanstack/react-query";
import * as Crypto from "expo-crypto";
import { router, useLocalSearchParams } from "expo-router";
import { useMemo, useRef, useState } from "react";
import { Alert, KeyboardAvoidingView, ScrollView, Text, TextInput, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ApiError, errorMessage } from "@/api/client";
import { useDeleteExpense, useSaveExpense } from "@/api/queries";
import type { Expense, ExpensePage } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import { WorkspaceGate } from "@/components/WorkspaceGate";
import { Avatar, Button, Chip, Field, Muted, Press, Screen, T } from "@/components/ui";
import { CATEGORIES, LEISURE_ICONS, type CategoryKey } from "@/constants/categories";
import { usePalette } from "@/constants/theme";
import { formatDateBR, fromISODate, toISODate } from "@/lib/dates";
import { digitsToCents, formatCentsPlain } from "@/lib/money";
import { colorFor, firstName } from "@/lib/people";
import { DESCRIPTION_MAX, validateExpense, type FieldErrors } from "@/lib/validation";

const QUICK = 6;

/** Procura o gasto no cache das listas (não existe GET /expenses/{id}). */
function useCachedExpense(id: string | undefined): Expense | undefined {
  const qc = useQueryClient();
  return useMemo(() => {
    if (!id) return undefined;
    for (const [, data] of qc.getQueriesData<InfiniteData<ExpensePage>>({ queryKey: ["expenses"] })) {
      const found = data?.pages.flatMap((p) => p.items).find((e) => e.id === id);
      if (found) return found;
    }
    return undefined;
  }, [qc, id]);
}

function ExpenseForm({ workspaceId, workspaceName, members, canEdit, archived }: {
  workspaceId: string;
  workspaceName: string;
  members: { user_id: string }[];
  canEdit: boolean;
  archived: boolean;
}) {
  const { id } = useLocalSearchParams<{ id?: string }>();
  const existing = useCachedExpense(id);
  const { user } = useAuth();
  const p = usePalette();
  const insets = useSafeAreaInsets();

  const [cents, setCents] = useState(existing?.amount_cents ?? 0);
  const [description, setDescription] = useState(existing?.description ?? "");
  const [date, setDate] = useState(existing?.spent_at ?? toISODate(new Date()));
  const [category, setCategory] = useState<CategoryKey | "">((existing?.category as CategoryKey) ?? "");
  const [iconKey, setIconKey] = useState<string | null>(existing?.icon_key ?? null);
  const [showAll, setShowAll] = useState(!!existing && CATEGORIES.findIndex((c) => c.key === existing.category) >= QUICK);
  const [showPicker, setShowPicker] = useState(false);
  const [maxDate] = useState(() => new Date(Date.now() + 31 * 86400000));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  // Mesma chave em todas as tentativas deste formulário: tocar 2x em salvar não duplica (RNF09).
  const idempotencyKey = useRef(Crypto.randomUUID()).current;

  const save = useSaveExpense(workspaceId);
  const del = useDeleteExpense();
  const editing = !!existing;

  if (!canEdit) {
    return (
      <View className="flex-1 items-center justify-center px-8">
        <Text style={{ fontSize: 40 }}>{archived ? "🗄️" : "👁️"}</Text>
        <T className="mt-3 text-center font-semibold text-lg">{archived ? "Ambiente arquivado" : "Somente leitura"}</T>
        <Muted className="mt-1 text-center">
          {archived
            ? `“${workspaceName}” está arquivado. O dono pode desarquivar nas configurações do ambiente.`
            : `Você pode acompanhar os gastos de “${workspaceName}”, mas não lançar.`}
        </Muted>
        <View className="mt-6 w-full"><Button title="Voltar" variant="ghost" onPress={() => router.back()} /></View>
      </View>
    );
  }

  const onSave = () => {
    const input = { amount_cents: cents, spent_at: date, description: description.trim(), category, icon_key: category === "LAZER" ? iconKey : null };
    const errs = validateExpense(input);
    setErrors(errs);
    setFormError(null);
    if (Object.keys(errs).length) return;
    save.mutate(
      { input, id: existing?.id, idempotencyKey },
      {
        onSuccess: () => router.back(),
        onError: (e) => {
          if (e instanceof ApiError && e.fields) setErrors(e.fields as FieldErrors);
          setFormError(errorMessage(e));
        },
      },
    );
  };

  const onDelete = () =>
    Alert.alert("Excluir gasto?", "Ele some do extrato e do resumo.", [
      { text: "Cancelar", style: "cancel" },
      {
        text: "Excluir",
        style: "destructive",
        onPress: () => del.mutate(existing!.id, { onSuccess: () => router.back(), onError: (e) => setFormError(errorMessage(e)) }),
      },
    ]);

  const cats = showAll ? CATEGORIES : CATEGORIES.slice(0, QUICK);

  return (
    <KeyboardAvoidingView behavior="padding" style={{ flex: 1 }}>
      <View style={{ paddingTop: insets.top + 8 }} className="flex-row items-center px-4 pb-2">
        <Press onPress={() => router.back()} accessibilityLabel="Fechar"><T className="px-2 text-2xl">✕</T></Press>
        <T className="ml-2 font-semibold text-lg">{editing ? "Editar gasto" : "Novo gasto"}</T>
      </View>

      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 20, paddingBottom: insets.bottom + 24 }}>
        {/* Valor primeiro e em destaque: registro em menos de 10 segundos (RNF02). */}
        <View className="mb-6 items-center">
          <Muted className="font-medium text-sm">Valor</Muted>
          <View className="mt-1 flex-row items-baseline">
            <T className="mr-2 font-semibold text-2xl text-ink-muted dark:text-night-muted">R$</T>
            <TextInput
              value={formatCentsPlain(cents)}
              onChangeText={(t) => setCents(digitsToCents(t))}
              keyboardType="number-pad"
              autoFocus={!editing}
              selectTextOnFocus={false}
              contextMenuHidden
              accessibilityLabel="Valor do gasto"
              style={{ color: errors.amount_cents ? p.danger : p.text, fontFamily: "Inter_700Bold", fontSize: 44, minWidth: 120, textAlign: "center" }}
            />
          </View>
          {errors.amount_cents ? <Text className="font-medium text-xs text-danger">{errors.amount_cents}</Text> : null}
        </View>

        <Field
          label="Descrição"
          right={<Muted className="text-xs">{[...description].length}/{DESCRIPTION_MAX}</Muted>}
          value={description}
          onChangeText={(t) => setDescription([...t].slice(0, DESCRIPTION_MAX).join(""))}
          placeholder="Ex.: Mercado da semana"
          maxLength={DESCRIPTION_MAX * 2}
          error={errors.description}
          returnKeyType="done"
        />

        <Muted className="mb-2 px-1 font-medium text-sm">Data</Muted>
        <Press onPress={() => setShowPicker(true)} accessibilityLabel="Escolher data">
          <View className={`mb-4 rounded-2xl border bg-paper-card px-4 py-3.5 dark:bg-night-card ${errors.spent_at ? "border-danger" : "border-paper-line dark:border-night-line"}`}>
            <T className="text-base">📅  {formatDateBR(date)}</T>
          </View>
        </Press>
        {showPicker ? (
          <DateTimePicker
            value={fromISODate(date)}
            mode="date"
            maximumDate={maxDate}
            minimumDate={new Date(2000, 0, 1)}
            onChange={(ev, d) => {
              setShowPicker(false);
              if (ev.type === "set" && d) setDate(toISODate(d));
            }}
          />
        ) : null}

        <View className="mb-2 flex-row justify-between px-1">
          <Muted className="font-medium text-sm">Categoria</Muted>
          <Press onPress={() => setShowAll((v) => !v)} haptic={false} accessibilityLabel="Ver todas as categorias">
            <Text className="font-semibold text-sm text-accent dark:text-white">{showAll ? "ver menos" : `ver todas (${CATEGORIES.length})`}</Text>
          </Press>
        </View>
        <View className="mb-1 flex-row flex-wrap gap-2">
          {cats.map((c) => (
            <Chip key={c.key} label={`${c.emoji} ${c.label}`} active={category === c.key} onPress={() => setCategory(c.key)} />
          ))}
        </View>
        {errors.category ? <Text className="px-1 font-medium text-xs text-danger">{errors.category}</Text> : null}

        {category === "LAZER" ? (
          <View className="mt-4">
            <Muted className="mb-2 px-1 font-medium text-sm">Ícone do lazer</Muted>
            <View className="flex-row flex-wrap gap-2">
              {LEISURE_ICONS.map((i) => {
                const active = iconKey === i.key;
                return (
                  <Press key={i.key} onPress={() => setIconKey(active ? null : i.key)} accessibilityLabel={i.label}>
                    <View className={`w-[76px] items-center rounded-2xl border py-2.5 ${active ? "border-accent bg-accent-soft dark:bg-accent-softDark" : "border-paper-line bg-paper-card dark:border-night-line dark:bg-night-card"}`}>
                      <Text style={{ fontSize: 22 }}>{i.emoji}</Text>
                      <Muted className="mt-1 text-[11px]">{i.label}</Muted>
                    </View>
                  </Press>
                );
              })}
            </View>
          </View>
        ) : null}

        <View className="my-6 flex-row items-center justify-center gap-2">
          <Avatar name={existing?.author.display_name ?? user?.display_name ?? "?"} color={colorFor(existing?.author.id ?? user?.id ?? "", members)} size={22} ring={false} />
          <Muted className="text-sm">
            Lançado por{" "}
            <Text className="font-semibold">{firstName(existing?.author.display_name ?? user?.display_name ?? "")}</Text> em{" "}
            <Text className="font-semibold">{workspaceName}</Text>
          </Muted>
        </View>

        {formError ? <Text className="mb-3 text-center font-medium text-sm text-danger">{formError}</Text> : null}
        <Button title={editing ? "Salvar alterações" : "Salvar gasto"} onPress={onSave} loading={save.isPending} />
        {editing ? (
          <View className="mt-3"><Button title="Excluir gasto" variant="danger" onPress={onDelete} loading={del.isPending} /></View>
        ) : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

export default function GastoScreen() {
  return (
    <Screen>
      <WorkspaceGate>
        {(ws) => (
          <ExpenseForm
            workspaceId={ws.id}
            workspaceName={ws.name}
            members={ws.members}
            canEdit={ws.role !== "VIEWER" && !ws.archived_at}
            archived={!!ws.archived_at}
          />
        )}
      </WorkspaceGate>
    </Screen>
  );
}
