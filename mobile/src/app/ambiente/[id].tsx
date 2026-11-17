import { router, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import { Alert, ScrollView, Text, View } from "react-native";

import { errorMessage } from "@/api/client";
import {
  useCancelInvite, useDeleteWorkspace, useLeaveWorkspace, usePendingInvites, useRemoveMember, useUpdateWorkspace, useWorkspace,
} from "@/api/queries";
import type { Workspace } from "@/api/types";
import { useAuth } from "@/auth/AuthProvider";
import { Header } from "@/components/Header";
import { IconPicker } from "@/components/IconPicker";
import { Avatar, Button, Card, ErrorState, Field, Loading, Muted, Press, Screen, SectionTitle, T } from "@/components/ui";
import { ROLE_LABEL } from "@/constants/categories";
import { colorFor } from "@/lib/people";
import { validateWorkspaceName, WORKSPACE_NAME_MAX } from "@/lib/validation";

function confirm(title: string, message: string, action: string, onOk: () => void) {
  Alert.alert(title, message, [{ text: "Cancelar", style: "cancel" }, { text: action, style: "destructive", onPress: onOk }]);
}

function Settings({ ws }: { ws: Workspace }) {
  const { user } = useAuth();
  const isOwner = ws.role === "OWNER";
  const [name, setName] = useState(ws.name);
  const [icon, setIcon] = useState(ws.icon);
  const [error, setError] = useState<string | null>(null);

  const update = useUpdateWorkspace(ws.id);
  const remove = useRemoveMember(ws.id);
  const del = useDeleteWorkspace();
  const leave = useLeaveWorkspace();
  const invites = usePendingInvites(ws.id, isOwner);
  const cancel = useCancelInvite(ws.id);

  const onError = (e: unknown) => setError(errorMessage(e));
  const dirty = name.trim() !== ws.name || icon !== ws.icon;

  return (
    <ScrollView contentContainerStyle={{ padding: 16, paddingBottom: 40 }}>
      {error ? <Text className="mb-3 text-center font-medium text-sm text-danger">{error}</Text> : null}

      {isOwner ? (
        <>
          <Field label="Nome" value={name} onChangeText={setName} maxLength={WORKSPACE_NAME_MAX} />
          <IconPicker value={icon} onChange={setIcon} />
          {dirty ? (
            <Button
              title="Salvar"
              loading={update.isPending}
              onPress={() => {
                const err = validateWorkspaceName(name);
                if (err) return setError(err);
                update.mutate({ name: name.trim(), icon }, { onSuccess: () => setError(null), onError });
              }}
            />
          ) : null}
        </>
      ) : null}

      <SectionTitle>Membros</SectionTitle>
      <Card className="gap-1 py-2">
        {ws.members.map((m) => (
          <View key={m.user_id} className="flex-row items-center gap-3 py-2">
            <Avatar name={m.display_name} color={colorFor(m.user_id, ws.members)} size={36} ring={false} />
            <View className="flex-1">
              <T className="font-medium" numberOfLines={1}>{m.display_name}{m.user_id === user?.id ? " (você)" : ""}</T>
              <Muted className="text-xs">{ROLE_LABEL[m.role]}</Muted>
            </View>
            {isOwner && m.role !== "OWNER" ? (
              <Press
                onPress={() => confirm("Remover acesso?", `${m.display_name} não verá mais este ambiente.`, "Remover", () => remove.mutate(m.user_id, { onError }))}
                accessibilityLabel={`Remover ${m.display_name}`}
              >
                <Text className="px-2 font-semibold text-sm text-danger">Remover</Text>
              </Press>
            ) : null}
          </View>
        ))}
      </Card>

      {isOwner && invites.data && invites.data.length > 0 ? (
        <>
          <SectionTitle>Convites pendentes</SectionTitle>
          <Card className="gap-1 py-2">
            {invites.data.map((inv) => (
              <View key={inv.id} className="flex-row items-center justify-between py-2">
                <View>
                  <T className="font-medium">{ROLE_LABEL[inv.role]}</T>
                  <Muted className="text-xs">expira {new Date(inv.expires_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" })}</Muted>
                </View>
                <Press onPress={() => cancel.mutate(inv.id, { onError })} accessibilityLabel="Cancelar convite">
                  <Text className="px-2 font-semibold text-sm text-danger">Cancelar</Text>
                </Press>
              </View>
            ))}
          </Card>
        </>
      ) : null}

      <SectionTitle>Zona de cuidado</SectionTitle>
      <View className="gap-3">
        {isOwner ? (
          <>
            <Button
              title={ws.archived_at ? "Desarquivar ambiente" : "Arquivar ambiente"}
              variant="ghost"
              loading={update.isPending}
              onPress={() => update.mutate({ archived: !ws.archived_at }, { onSuccess: () => router.navigate("/"), onError })}
            />
            <Button
              title="Excluir ambiente"
              variant="danger"
              loading={del.isPending}
              onPress={() =>
                confirm("Excluir ambiente?", `“${ws.name}” some para todos os membros.`, "Excluir", () =>
                  del.mutate(ws.id, { onSuccess: () => router.navigate("/"), onError }),
                )
              }
            />
          </>
        ) : (
          <Button
            title="Sair do ambiente"
            variant="danger"
            loading={leave.isPending}
            onPress={() => confirm("Sair do ambiente?", "Você vai precisar de um novo convite para voltar.", "Sair", () => leave.mutate(ws.id, { onSuccess: () => router.navigate("/"), onError }))}
          />
        )}
      </View>
    </ScrollView>
  );
}

export default function WorkspaceSettings() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const ws = useWorkspace(id);
  return (
    <Screen>
      <Header title={ws.data ? `${ws.data.icon} ${ws.data.name}` : "Ambiente"} />
      {ws.isPending ? <Loading /> : ws.error ? <ErrorState message={errorMessage(ws.error)} onRetry={ws.refetch} /> : <Settings ws={ws.data} />}
    </Screen>
  );
}
