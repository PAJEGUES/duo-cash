import { View } from "react-native";
import Svg, { Circle, G } from "react-native-svg";

import { usePalette } from "@/constants/theme";
import { T } from "./ui";

/** Gráfico de rosca simples, sem biblioteca extra. */
export function Donut({ slices, center, size = 140 }: { slices: { value: number; color: string }[]; center: string; size?: number }) {
  const p = usePalette();
  const stroke = 18;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const total = slices.reduce((s, x) => s + x.value, 0);
  let offset = 0;
  return (
    <View style={{ width: size, height: size }} className="items-center justify-center">
      <Svg width={size} height={size} style={{ position: "absolute" }}>
        <G rotation={-90} origin={`${size / 2}, ${size / 2}`}>
          <Circle cx={size / 2} cy={size / 2} r={r} stroke={p.track} strokeWidth={stroke} fill="none" />
          {total > 0 &&
            slices.map((s, i) => {
              const len = (s.value / total) * c;
              const el = (
                <Circle
                  key={i}
                  cx={size / 2}
                  cy={size / 2}
                  r={r}
                  stroke={s.color}
                  strokeWidth={stroke}
                  fill="none"
                  strokeDasharray={`${len} ${c - len}`}
                  strokeDashoffset={-offset}
                />
              );
              offset += len;
              return el;
            })}
        </G>
      </Svg>
      <T className="font-bold text-2xl">{center}</T>
      <T className="text-xs text-ink-muted dark:text-night-muted">gastos</T>
    </View>
  );
}

export function ProgressBar({ value, color }: { value: number; color: string }) {
  return (
    <View className="h-2 overflow-hidden rounded-full bg-accent-soft dark:bg-accent-softDark">
      <View style={{ width: `${Math.max(0, Math.min(100, value))}%`, backgroundColor: color }} className="h-2 rounded-full" />
    </View>
  );
}

export function MonthBars({ data }: { data: { label: string; value: number; current: boolean }[] }) {
  const p = usePalette();
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <View className="h-36 flex-row items-end justify-between px-2">
      {data.map((d) => (
        <View key={d.label} className="items-center gap-2" style={{ width: 36 }}>
          <View
            style={{ height: Math.max(4, (d.value / max) * 96), backgroundColor: d.current ? p.accent : p.track, width: 26 }}
            className="rounded-lg"
          />
          <T className={`text-xs ${d.current ? "font-bold text-accent dark:text-white" : "text-ink-muted dark:text-night-muted"}`}>{d.label}</T>
        </View>
      ))}
    </View>
  );
}
