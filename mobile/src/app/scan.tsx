import { CameraView, useCameraPermissions } from "expo-camera";
import { router } from "expo-router";
import { useRef, useState } from "react";
import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Button, EmptyState, Press, Screen } from "@/components/ui";
import { parseInviteToken } from "@/lib/validation";

export default function ScanScreen() {
  const [permission, requestPermission] = useCameraPermissions();
  const [error, setError] = useState<string | null>(null);
  const handled = useRef(false);
  const insets = useSafeAreaInsets();

  if (!permission) return <Screen />;
  if (!permission.granted) {
    return (
      <Screen className="justify-center">
        <EmptyState
          emoji="📷"
          title="Precisamos da câmera"
          text="A câmera é usada só para ler o QR Code do convite."
          action={
            <View className="gap-3">
              <Button title="Permitir câmera" onPress={requestPermission} />
              <Button title="Voltar" variant="ghost" onPress={() => router.back()} />
            </View>
          }
        />
      </Screen>
    );
  }

  return (
    <View className="flex-1 bg-black">
      <CameraView
        style={{ flex: 1 }}
        facing="back"
        barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
        onBarcodeScanned={({ data }) => {
          if (handled.current) return;
          const token = parseInviteToken(data);
          if (!token) return setError("Esse QR Code não é um convite do DuoCash.");
          handled.current = true;
          router.replace({ pathname: "/join/[token]", params: { token } });
        }}
      />
      <View style={{ position: "absolute", top: insets.top + 12, left: 16, right: 16 }} className="flex-row items-center justify-between">
        <Press onPress={() => router.back()} accessibilityLabel="Fechar"><Text className="px-2 text-2xl text-white">✕</Text></Press>
        <Text className="font-semibold text-base text-white">Ler convite</Text>
        <View className="w-8" />
      </View>
      <View pointerEvents="none" style={{ position: "absolute", top: "30%", alignSelf: "center" }} className="h-64 w-64 rounded-3xl border-4 border-white/80" />
      <View style={{ position: "absolute", bottom: insets.bottom + 40, left: 24, right: 24 }} className="rounded-2xl bg-black/60 p-4">
        <Text className="text-center font-medium text-sm text-white">{error ?? "Aponte a câmera para o QR Code do convite."}</Text>
      </View>
    </View>
  );
}
