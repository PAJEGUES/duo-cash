import { Tabs, type BottomTabBarProps } from "expo-router/js-tabs";
import { router } from "expo-router";
import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { Press } from "@/components/ui";
import { usePalette } from "@/constants/theme";

const ITEMS: Record<string, { label: string; emoji: string }> = {
  index: { label: "Início", emoji: "🏠" },
  extrato: { label: "Extrato", emoji: "🔎" },
  resumo: { label: "Resumo", emoji: "📊" },
  convidar: { label: "Convidar", emoji: "👥" },
};

/** Menu de baixo com o botão + sempre no centro (registrar gasto é a ação mais usada). */
function TabBar({ state, navigateToTab }: BottomTabBarProps) {
  const p = usePalette();
  const insets = useSafeAreaInsets();
  const routes = state.routes.filter((r) => ITEMS[r.name]);

  const renderTab = (route: (typeof routes)[number]) => {
    const focused = state.routes[state.index]?.key === route.key;
    const item = ITEMS[route.name];
    return (
      <Press key={route.key} haptic={false} accessibilityLabel={item.label} onPress={() => navigateToTab(route.key)}>
        <View className="w-16 items-center gap-0.5 py-1">
          <Text style={{ fontSize: 20, opacity: focused ? 1 : 0.45 }}>{item.emoji}</Text>
          <Text className={`text-[11px] ${focused ? "font-bold text-accent dark:text-white" : "font-medium text-ink-muted dark:text-night-muted"}`}>
            {item.label}
          </Text>
        </View>
      </Press>
    );
  };

  return (
    <View
      style={{ paddingBottom: insets.bottom + 6, backgroundColor: p.card, borderTopColor: p.line }}
      className="flex-row items-center justify-around border-t pt-2"
    >
      {routes.slice(0, 2).map(renderTab)}
      <Press accessibilityLabel="Registrar gasto" onPress={() => router.push("/gasto")}>
        <View
          className="-mt-8 h-16 w-16 items-center justify-center rounded-full bg-accent"
          style={{ shadowColor: p.accent, shadowOpacity: 0.45, shadowRadius: 14, shadowOffset: { width: 0, height: 6 }, elevation: 8 }}
        >
          <Text className="font-sans text-3xl text-white">+</Text>
        </View>
      </Press>
      {routes.slice(2).map(renderTab)}
    </View>
  );
}

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{ headerShown: false }} tabBar={(props) => <TabBar {...props} />}>
      <Tabs.Screen name="index" />
      <Tabs.Screen name="extrato" />
      <Tabs.Screen name="resumo" />
      <Tabs.Screen name="convidar" />
    </Tabs>
  );
}
