import { BlurView } from "expo-blur";
import * as Haptics from "expo-haptics";
import { LinearGradient } from "expo-linear-gradient";
import type { ReactNode } from "react";
import { ActivityIndicator, Pressable, Text, TextInput, View, type TextInputProps, type TextProps, type ViewProps } from "react-native";
import Animated, { FadeInDown, useAnimatedStyle, useSharedValue, withSpring } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { usePalette } from "@/constants/theme";
import { initial } from "@/lib/people";

/** Texto padrão com a fonte Inter e cor que acompanha o modo escuro. */
export function T({ className = "", ...props }: TextProps & { className?: string }) {
  return <Text className={`font-sans text-ink dark:text-white ${className}`} {...props} />;
}

export function Muted({ className = "", ...props }: TextProps & { className?: string }) {
  return <T className={`text-ink-muted dark:text-night-muted ${className}`} {...props} />;
}

export function Screen({ children, className = "", ...props }: ViewProps & { className?: string }) {
  return (
    <View className={`flex-1 bg-paper dark:bg-night ${className}`} {...props}>
      {children}
    </View>
  );
}

/** Topo com gradiente suave (hero) usado nas telas principais. */
export function Hero({ children }: { children: ReactNode }) {
  const p = usePalette();
  const insets = useSafeAreaInsets();
  return (
    <LinearGradient
      colors={p.hero}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      style={{ paddingTop: insets.top + 12, paddingBottom: 24, paddingHorizontal: 20, borderBottomLeftRadius: 28, borderBottomRightRadius: 28 }}
    >
      {children}
    </LinearGradient>
  );
}

/** Cartão de vidro (glassmorphism) para destacar números dentro do hero. */
export function Glass({ children }: { children: ReactNode }) {
  return (
    <View style={{ borderRadius: 20, overflow: "hidden", borderWidth: 1, borderColor: "rgba(255,255,255,0.22)" }}>
      <BlurView intensity={24} tint="light" style={{ padding: 18, backgroundColor: "rgba(255,255,255,0.12)" }}>
        {children}
      </BlurView>
    </View>
  );
}

export function Card({ children, className = "", ...props }: ViewProps & { className?: string }) {
  return (
    <View
      className={`rounded-2xl border border-paper-line bg-paper-card p-4 dark:border-night-line dark:bg-night-card ${className}`}
      style={{ shadowColor: "#2A145A", shadowOpacity: 0.06, shadowRadius: 12, shadowOffset: { width: 0, height: 4 }, elevation: 1 }}
      {...props}
    >
      {children}
    </View>
  );
}

/** Entrada animada (fade + leve subida) para listas e cartões. */
export function FadeIn({ children, index = 0 }: { children: ReactNode; index?: number }) {
  return <Animated.View entering={FadeInDown.duration(320).delay(Math.min(index, 10) * 45)}>{children}</Animated.View>;
}

const SPRING = { damping: 20, stiffness: 300 };

/** Pressable com micro-interação: encolhe levemente e dá um toque háptico. */
export function Press({
  children, onPress, disabled, className = "", haptic = true, accessibilityLabel,
}: {
  children: ReactNode;
  onPress?: () => void;
  disabled?: boolean;
  className?: string;
  haptic?: boolean;
  accessibilityLabel?: string;
}) {
  const scale = useSharedValue(1);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.get() }] }));
  return (
    <Animated.View style={style}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={accessibilityLabel}
        disabled={disabled}
        className={className}
        onPressIn={() => scale.set(withSpring(0.97, SPRING))}
        onPressOut={() => scale.set(withSpring(1, SPRING))}
        onPress={() => {
          if (haptic) Haptics.selectionAsync().catch(() => undefined);
          onPress?.();
        }}
      >
        {children}
      </Pressable>
    </Animated.View>
  );
}

const BUTTON_STYLES = {
  primary: { box: "bg-accent", text: "text-white" },
  outline: { box: "border-[1.5px] border-accent bg-transparent", text: "text-accent dark:text-white" },
  ghost: { box: "bg-accent-soft dark:bg-accent-softDark", text: "text-accent dark:text-white" },
  danger: { box: "border-[1.5px] border-danger bg-transparent", text: "text-danger" },
  light: { box: "bg-white", text: "text-ink" },
} as const;

export function Button({
  title, onPress, variant = "primary", loading, disabled, icon,
}: {
  title: string;
  onPress?: () => void;
  variant?: keyof typeof BUTTON_STYLES;
  loading?: boolean;
  disabled?: boolean;
  icon?: ReactNode;
}) {
  const s = BUTTON_STYLES[variant];
  const off = disabled || loading;
  return (
    <Press onPress={onPress} disabled={off} accessibilityLabel={title}>
      <View className={`flex-row items-center justify-center gap-2 rounded-2xl px-5 py-4 ${s.box} ${off ? "opacity-50" : ""}`}>
        {loading ? <ActivityIndicator color={variant === "primary" ? "#fff" : "#6D4FC2"} /> : icon}
        <Text className={`font-semibold text-base ${s.text}`}>{title}</Text>
      </View>
    </Press>
  );
}

export function Avatar({ name, color, size = 32, ring = true }: { name: string; color: string; size?: number; ring?: boolean }) {
  return (
    <View
      style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: color, borderWidth: ring ? 2 : 0, borderColor: "#fff" }}
      className="items-center justify-center"
    >
      <Text className="font-bold text-white" style={{ fontSize: size * 0.42 }}>
        {initial(name)}
      </Text>
    </View>
  );
}

export function Chip({ label, active, onPress }: { label: string; active?: boolean; onPress?: () => void }) {
  return (
    <Press onPress={onPress} accessibilityLabel={label}>
      <View
        className={`rounded-full border px-4 py-2 ${
          active ? "border-accent bg-accent" : "border-paper-line bg-paper-card dark:border-night-line dark:bg-night-card"
        }`}
      >
        <Text className={`font-medium text-sm ${active ? "text-white" : "text-ink dark:text-white"}`}>{label}</Text>
      </View>
    </Press>
  );
}

export function SectionTitle({ children, right }: { children: ReactNode; right?: ReactNode }) {
  return (
    <View className="mb-3 mt-6 flex-row items-center justify-between px-1">
      <Text className="font-semibold text-xs uppercase tracking-widest text-ink-muted dark:text-night-muted">{children}</Text>
      {right}
    </View>
  );
}

export function Field({
  label, error, right, ...props
}: TextInputProps & { label: string; error?: string; right?: ReactNode }) {
  const p = usePalette();
  return (
    <View className="mb-4">
      <View className="mb-2 flex-row justify-between px-1">
        <Text className="font-medium text-sm text-ink-muted dark:text-night-muted">{label}</Text>
        {right}
      </View>
      <TextInput
        placeholderTextColor={p.muted}
        className={`rounded-2xl border bg-paper-card px-4 py-3.5 font-sans text-base text-ink dark:bg-night-card dark:text-white ${
          error ? "border-danger" : "border-paper-line dark:border-night-line"
        }`}
        {...props}
      />
      {error ? <Text className="mt-1.5 px-1 font-medium text-xs text-danger">{error}</Text> : null}
    </View>
  );
}

export function Loading() {
  const p = usePalette();
  return (
    <View className="flex-1 items-center justify-center py-16">
      <ActivityIndicator color={p.accent} size="large" />
    </View>
  );
}

export function EmptyState({ emoji, title, text, action }: { emoji: string; title: string; text?: string; action?: ReactNode }) {
  return (
    <View className="items-center px-8 py-12">
      <Text style={{ fontSize: 44 }}>{emoji}</Text>
      <T className="mt-3 text-center font-semibold text-lg">{title}</T>
      {text ? <Muted className="mt-1 text-center text-sm leading-5">{text}</Muted> : null}
      {action ? <View className="mt-5 w-full">{action}</View> : null}
    </View>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <EmptyState
      emoji="📡"
      title="Não deu para carregar"
      text={message}
      action={onRetry ? <Button title="Tentar de novo" variant="ghost" onPress={onRetry} /> : undefined}
    />
  );
}
