import * as Clipboard from "expo-clipboard";
import { router } from "expo-router";
import { useEffect, useState } from "react";
import { ScrollView, Share, Text, View } from "react-native";
import QRCode from "react-native-qrcode-svg";

import { errorMessage } from "@/api/client";
import { useCreateInvite } from "@/api/queries";
import type { CreatedInvite, Workspace } from "@/api/types";
import { WorkspaceGate } from "@/components/WorkspaceGate";
import { Button, Card, FadeIn, Hero, Loading, Muted, Press, Screen, SectionTitle, T } from "@/components/ui";

type InviteRole = "EDITOR" | "VIEWER";

function minutesLeft(iso: string) {
  return Math.max(0, Math.round((new Date(iso).getTime() - Date.now()) / 60000));
}

function Invite({ ws }: { ws: Workspace }) {
  const [role, setRole] = useState<InviteRole>("EDITOR");
  const [invite, setInvite] = useState<CreatedInvite | null>(null);
  const [copied, setCopied] = useState(false);
  const [, tick] = useState(0);
  const create = useCreateInvite(ws.id);
  const isOwner = ws.role === "OWNER";

  // Atualiza o contador de expiração a cada 30 s.
  useEffect(() => {
    const t = setInterval(() => tick((n) => n + 1), 30_000);
    return () => clearInterval(t);
  }, []);

  const generate = (r: InviteRole) => {
    setRole(r);
    setInvite(null);
    create.mutate(r, { onSuccess: setInvite });
  };

  const expired = invite ? minutesLeft(invite.expires_at) <= 0 : false;

  return (
    <ScrollView contentContainerStyle={{ paddingBottom: 32 }}>
      <Hero>
        <Text className="font-bold text-2xl text-white">Convidar</Text>
        <Text className="mt-1 font-sans text-sm text-white/75">para “{ws.icon} {ws.name}”</Text>
      </Hero>

      <View className="px-4">
        {!isOwner ? (
          <Card className="mt-5">
            <T className="font-semibold">Só o dono do ambiente pode convidar.</T>
            <Muted className="mt-1 text-sm">Peça para quem criou “{ws.name}” gerar o convite.</Muted>
          </Card>
        ) : (
          <>
            <SectionTitle>Permissão do convidado</SectionTitle>
            <View className="flex-row gap-3">
              {([
                ["EDITOR", "✏️ Controle total", "Vê e registra gastos"],
                ["VIEWER", "👁️ Somente leitura", "Apenas acompanha"],
              ] as const).map(([key, title, desc]) => (
                <View key={key} className="flex-1">
                  <Press onPress={() => generate(key)} accessibilityLabel={title}>
                    <View className={`rounded-2xl border-[1.5px] p-4 ${role === key && (invite || create.isPending) ? "border-accent bg-accent-soft dark:bg-accent-softDark" : "border-paper-line bg-paper-card dark:border-night-line dark:bg-night-card"}`}>
                      <T className="font-semibold text-sm">{title}</T>
                      <Muted className="mt-1 text-xs">{desc}</Muted>
                    </View>
                  </Press>
                </View>
              ))}
            </View>

            <SectionTitle>Convite</SectionTitle>
            <Card className="items-center py-6">
              {create.isPending ? (
                <Loading />
              ) : invite && !expired ? (
                <FadeIn>
                  <View className="items-center">
                    <View className="rounded-2xl bg-white p-3">
                      <QRCode value={invite.app_url} size={190} color="#18161F" backgroundColor="#FFFFFF" />
                    </View>
                    <Muted className="mt-4 text-center text-sm leading-5">
                      Peça para a outra pessoa abrir o DuoCash,{"\n"}tocar em “Recebi um convite” e apontar a câmera.
                    </Muted>
                    <T className="mt-3 text-center text-xs">⏱️ Expira em <Text className="font-bold">{minutesLeft(invite.expires_at)} min</Text> e só pode ser usado uma vez.</T>
                  </View>
                </FadeIn>
              ) : (
                <View className="items-center px-4">
                  <Text style={{ fontSize: 36 }}>💌</Text>
                  <Muted className="mt-2 text-center text-sm">
                    {create.error ? errorMessage(create.error) : expired ? "Este convite expirou. Gere outro." : "Escolha a permissão acima para gerar o QR Code."}
                  </Muted>
                </View>
              )}
            </Card>

            {invite && !expired ? (
              <View className="gap-3">
                <Button
                  title="Compartilhar link"
                  onPress={() => Share.share({ message: `Entre no meu ambiente “${ws.name}” no DuoCash: ${invite.share_url}` })}
                />
                <Button
                  title={copied ? "Link copiado ✓" : "Copiar link"}
                  variant="ghost"
                  onPress={async () => {
                    await Clipboard.setStringAsync(invite.share_url);
                    setCopied(true);
                    setTimeout(() => setCopied(false), 2000);
                  }}
                />
              </View>
            ) : null}
          </>
        )}

        <View className="mt-3">
          <Button title="📷 Ler QR Code de um convite" variant="outline" onPress={() => router.push("/scan")} />
        </View>
      </View>
    </ScrollView>
  );
}

export default function ConvidarScreen() {
  return (
    <Screen>
      <WorkspaceGate>{(ws) => <Invite ws={ws} />}</WorkspaceGate>
    </Screen>
  );
}
