import { Text, View } from "react-native";

import { WORKSPACE_ICONS } from "@/constants/categories";
import { Press } from "./ui";

export function IconPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <View className="mb-6 flex-row flex-wrap gap-2">
      {WORKSPACE_ICONS.map((i) => (
        <Press key={i} onPress={() => onChange(i)} accessibilityLabel={`Ícone ${i}`}>
          <View className={`h-14 w-14 items-center justify-center rounded-2xl border-[1.5px] ${value === i ? "border-accent bg-accent-soft dark:bg-accent-softDark" : "border-paper-line bg-paper-card dark:border-night-line dark:bg-night-card"}`}>
            <Text style={{ fontSize: 24 }}>{i}</Text>
          </View>
        </Press>
      ))}
    </View>
  );
}
