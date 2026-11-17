import { useColorScheme } from "react-native";

const light = {
  accent: "#6D4FC2",
  accentStrong: "#4B2F9E",
  partner: "#1FA97A",
  danger: "#D9455F",
  text: "#18161F",
  muted: "#6B6878",
  bg: "#F7F6FA",
  card: "#FFFFFF",
  line: "#E8E5EF",
  hero: ["#7B5CD6", "#5A3BB8", "#3E2491"] as readonly [string, string, string],
  track: "#EFEAFC",
};

const dark: typeof light = {
  accent: "#8B6CF0",
  accentStrong: "#6D4FC2",
  partner: "#2BC48F",
  danger: "#F06A80",
  text: "#F4F2FA",
  muted: "#A19DB0",
  bg: "#0E0C14",
  card: "#17151F",
  line: "#2A2735",
  hero: ["#3A2580", "#251653", "#120B2B"] as const,
  track: "#2A2140",
};

export type Palette = typeof light;

export function usePalette(): Palette & { isDark: boolean } {
  const isDark = useColorScheme() === "dark";
  return { ...(isDark ? dark : light), isDark };
}
