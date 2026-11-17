import { LinearGradient } from "expo-linear-gradient";
import { useEffect, useState } from "react";
import { ScrollView, Text, TextInput, View } from "react-native";
import Animated, { FadeIn, FadeInUp } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { errorMessage } from "@/api/client";
import { canEditServer, getServerUrl, setServerUrl } from "@/api/storage";
import { useAuth } from "@/auth/AuthProvider";
import { Button, Press } from "@/components/ui";
import { usePalette } from "@/constants/theme";
import { normalizeServerUrl } from "@/lib/validation";

export default function Login() {
  const { signInWithGoogle } = useAuth();
  const p = usePalette();
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [server, setServer] = useState("");
  const [editingServer, setEditingServer] = useState(false);
  const [canEdit, setCanEdit] = useState(false);

  useEffect(() => {
    Promise.all([getServerUrl(), canEditServer()]).then(([url, editable]) => {
      setServer(url);
      setCanEdit(editable);
      if (!url) setEditingServer(true);
    });
  }, []);

  async function saveServer(): Promise<boolean> {
    const url = normalizeServerUrl(server, __DEV__);
    if (!url) {
      setError("Endereço inválido. Use o formato https://exemplo.com");
      return false;
    }
    await setServerUrl(url);
    setServer(url);
    setEditingServer(false);
    return true;
  }

  async function onLogin() {
    setError(null);
    if (editingServer && !(await saveServer())) return;
    setLoading(true);
    try {
      await signInWithGoogle();
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <LinearGradient colors={p.hero} start={{ x: 0, y: 0 }} end={{ x: 0.6, y: 1 }} style={{ flex: 1 }}>
      {/* ScrollView: em telas baixas (ou com o teclado aberto) o botão nunca fica escondido. */}
      <ScrollView
        keyboardShouldPersistTaps="handled"
        contentContainerStyle={{ flexGrow: 1, paddingTop: insets.top + 24, paddingBottom: insets.bottom + 24 }}
      >
        <View className="flex-1 items-center justify-center px-8 py-8">
          <Animated.View entering={FadeIn.duration(600)} className="h-24 w-24 items-center justify-center rounded-[28px] border border-white/25 bg-white/15">
            <Text style={{ fontSize: 48 }}>💑</Text>
          </Animated.View>
          <Animated.Text entering={FadeInUp.delay(150).duration(500)} className="mt-6 font-sans text-4xl text-white">
            Duo<Text className="font-bold">Cash</Text>
          </Animated.Text>
          <Animated.Text entering={FadeInUp.delay(250).duration(500)} className="mt-3 text-center font-sans text-base leading-6 text-white/80">
            As finanças do casal em um só lugar.{"\n"}Registrem juntos, acompanhem juntos.
          </Animated.Text>
        </View>

        <Animated.View entering={FadeInUp.delay(350).duration(500)} className="px-6">
          {editingServer ? (
            <View className="mb-4">
              <Text className="mb-2 font-medium text-sm text-white/80">Endereço do servidor</Text>
              <TextInput
                value={server}
                onChangeText={setServer}
                placeholder="https://..."
                placeholderTextColor="rgba(255,255,255,0.5)"
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
                className="rounded-2xl border border-white/25 bg-white/10 px-4 py-3.5 font-sans text-base text-white"
              />
              <Text className="mt-2 font-sans text-xs leading-5 text-white/70">
                ⚠️ Use só o endereço do seu próprio servidor. Depois de salvo, ele não pode ser trocado.
              </Text>
            </View>
          ) : null}

          {error ? (
            <View className="mb-4 rounded-2xl bg-white/15 p-3">
              <Text className="text-center font-medium text-sm text-white">{error}</Text>
            </View>
          ) : null}

          <Button title="Entrar com Google" variant="light" onPress={onLogin} loading={loading} icon={<Text className="font-bold text-lg text-accent">G</Text>} />

          <Text className="mt-4 text-center font-sans text-xs leading-5 text-white/70">
            O DuoCash não tem senha própria.{"\n"}O login é feito somente pela sua conta Google.
          </Text>

          {!editingServer && server ? (
            <Press onPress={canEdit ? () => setEditingServer(true) : undefined} disabled={!canEdit} haptic={false} accessibilityLabel="Servidor">
              <Text className={`mt-3 text-center font-medium text-xs text-white/60 ${canEdit ? "underline" : ""}`}>Servidor: {server.replace(/^https?:\/\//, "")}</Text>
            </Press>
          ) : null}
        </Animated.View>
      </ScrollView>
    </LinearGradient>
  );
}
