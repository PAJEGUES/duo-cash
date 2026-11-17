import { router } from "expo-router";
import { useState } from "react";
import { KeyboardAvoidingView, ScrollView } from "react-native";

import { errorMessage } from "@/api/client";
import { useCreateWorkspace } from "@/api/queries";
import { Header } from "@/components/Header";
import { IconPicker } from "@/components/IconPicker";
import { Button, Field, Muted, Screen } from "@/components/ui";
import { WORKSPACE_ICONS } from "@/constants/categories";
import { useCurrentWorkspace } from "@/lib/currentWorkspace";
import { validateWorkspaceName, WORKSPACE_NAME_MAX } from "@/lib/validation";

export default function NewWorkspace() {
  const [name, setName] = useState("");
  const [icon, setIcon] = useState<string>(WORKSPACE_ICONS[0]);
  const [error, setError] = useState<string | null>(null);
  const create = useCreateWorkspace();
  const { select } = useCurrentWorkspace();

  const onCreate = () => {
    const err = validateWorkspaceName(name);
    setError(err);
    if (err) return;
    create.mutate(
      { name: name.trim(), icon },
      {
        onSuccess: (ws) => {
          select(ws.id);
          router.back();
        },
        onError: (e) => setError(errorMessage(e)),
      },
    );
  };

  return (
    <Screen>
      <Header title="Novo ambiente" close />
      <KeyboardAvoidingView behavior="padding" style={{ flex: 1 }}>
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ padding: 20 }}>
          <Field label="Nome" value={name} onChangeText={setName} placeholder="Ex.: Casa, Viagem Chile 2026" maxLength={WORKSPACE_NAME_MAX} autoFocus error={error ?? undefined} />
          <Muted className="mb-2 px-1 font-medium text-sm">Ícone</Muted>
          <IconPicker value={icon} onChange={setIcon} />
          <Button title="Criar ambiente" onPress={onCreate} loading={create.isPending} />
          <Muted className="mt-4 text-center text-xs">Você será o dono e poderá convidar outra pessoa.</Muted>
        </ScrollView>
      </KeyboardAvoidingView>
    </Screen>
  );
}
