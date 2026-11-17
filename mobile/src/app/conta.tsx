import * as Application from "expo-application";
import { useEffect, useState } from "react";
import { ScrollView, View } from "react-native";

import { getServerUrl } from "@/api/storage";
import { useAuth } from "@/auth/AuthProvider";
import { Header } from "@/components/Header";
import { Avatar, Button, Card, Muted, Screen, T } from "@/components/ui";
import { usePalette } from "@/constants/theme";

export default function Account() {
  const { user, signOut } = useAuth();
  const p = usePalette();
  const [server, setServer] = useState("");

  useEffect(() => {
    getServerUrl().then(setServer);
  }, []);

  return (
    <Screen>
      <Header title="Minha conta" />
      <ScrollView contentContainerStyle={{ padding: 16 }}>
        <Card className="items-center py-8">
          <Avatar name={user?.display_name ?? "?"} color={p.accent} size={72} ring={false} />
          <T className="mt-3 font-bold text-xl">{user?.display_name}</T>
          <Muted className="mt-1 text-sm">{user?.email}</Muted>
        </Card>
        <Card className="mt-4 gap-2">
          <View className="flex-row justify-between"><Muted className="text-sm">Versão do app</Muted><T className="text-sm">{Application.nativeApplicationVersion} ({Application.nativeBuildVersion})</T></View>
          <View className="flex-row justify-between"><Muted className="text-sm">Servidor</Muted><T className="text-sm" numberOfLines={1}>{server.replace(/^https?:\/\//, "")}</T></View>
        </Card>
        <View className="mt-6">
          <Button title="Sair da conta" variant="danger" onPress={signOut} />
        </View>
      </ScrollView>
    </Screen>
  );
}
