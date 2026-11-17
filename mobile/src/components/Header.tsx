import { router } from "expo-router";
import { View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Press, T } from "./ui";

export function Header({ title, close = false }: { title: string; close?: boolean }) {
  const insets = useSafeAreaInsets();
  return (
    <View style={{ paddingTop: insets.top + 8 }} className="flex-row items-center px-4 pb-3">
      <Press onPress={() => router.back()} accessibilityLabel={close ? "Fechar" : "Voltar"}>
        <T className="px-2 text-2xl">{close ? "✕" : "‹"}</T>
      </Press>
      <T className="ml-2 flex-1 font-semibold text-lg" numberOfLines={1}>{title}</T>
    </View>
  );
}
