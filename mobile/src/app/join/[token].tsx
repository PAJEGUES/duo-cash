import { router, useLocalSearchParams } from "expo-router";
import { Text, View } from "react-native";

import { ApiError, errorMessage } from "@/api/client";
import { useAcceptInvite, useInvitePreview } from "@/api/queries";
import { useAuth } from "@/auth/AuthProvider";
import { Button, Card, EmptyState, Loading, Muted, Screen, T } from "@/components/ui";
import { ROLE_LABEL } from "@/constants/categories";
import { useCurrentWorkspace } from "@/lib/currentWorkspace";
import { setPendingInvite } from "@/lib/pendingInvite";

const TOKEN_RE = /^[A-Za-z0-9_-]{16,128}$/;

function Accept({ token }: { token: string }) {
  const preview = useInvitePreview(token);
  const accept = useAcceptInvite();
  const { select } = useCurrentWorkspace();

  if (preview.isPending) return <Loading />;
  if (preview.error) {
    const gone = preview.error instanceof ApiError && (preview.error.status === 410 || preview.error.status === 404);
    return (
      <EmptyState
        emoji="⌛"
        title={gone ? "Convite inválido" : "Não deu para abrir o convite"}
        text={gone ? "Este convite expirou, já foi usado ou foi cancelado. Peça um novo." : errorMessage(preview.error)}
        action={<Button title="Ir para Início" variant="ghost" onPress={() => router.replace("/")} />}
      />
    );
  }
  const inv = preview.data;
  return (
    <View className="px-6">
      <Card className="items-center py-8">
        <Text style={{ fontSize: 48 }}>{inv.workspace_icon}</Text>
        <Muted className="mt-3 text-sm">{inv.invited_by} convidou você para</Muted>
        <T className="mt-1 text-center font-bold text-2xl">{inv.workspace_name}</T>
        <View className="mt-3 rounded-full bg-accent-soft px-3 py-1 dark:bg-accent-softDark">
          <Text className="font-semibold text-xs text-accent dark:text-white">{ROLE_LABEL[inv.role]}</Text>
        </View>
      </Card>
      {accept.error ? <Text className="mt-4 text-center font-medium text-sm text-danger">{errorMessage(accept.error)}</Text> : null}
      <View className="mt-6 gap-3">
        <Button
          title="Entrar no ambiente"
          loading={accept.isPending}
          onPress={() =>
            accept.mutate(token, {
              onSuccess: ({ workspace }) => {
                select(workspace.id);
                router.replace("/resumo");
              },
            })
          }
        />
        <Button title="Agora não" variant="ghost" onPress={() => router.replace("/")} />
      </View>
    </View>
  );
}

export default function JoinScreen() {
  const { token } = useLocalSearchParams<{ token: string }>();
  const { status } = useAuth();
  const valid = typeof token === "string" && TOKEN_RE.test(token);

  if (!valid) {
    return (
      <Screen className="justify-center">
        <EmptyState emoji="🔗" title="Link inválido" action={<Button title="Voltar" variant="ghost" onPress={() => router.replace("/")} />} />
      </Screen>
    );
  }
  if (status !== "signedIn") {
    return (
      <Screen className="justify-center">
        <EmptyState
          emoji="💌"
          title="Você recebeu um convite"
          text="Entre com sua conta Google para aceitar."
          action={
            <Button
              title="Entrar"
              onPress={() => {
                setPendingInvite(token);
                router.replace("/login");
              }}
            />
          }
        />
      </Screen>
    );
  }
  return (
    <Screen className="justify-center">
      <Accept token={token} />
    </Screen>
  );
}
