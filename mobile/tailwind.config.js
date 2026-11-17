/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  presets: [require("nativewind/preset")],
  darkMode: "media",
  theme: {
    extend: {
      colors: {
        accent: { DEFAULT: "#6D4FC2", strong: "#4B2F9E", soft: "#EFEAFC", softDark: "#2A2140" },
        partner: { DEFAULT: "#1FA97A", soft: "#E2F6EE", softDark: "#123B2E" },
        danger: "#D9455F",
        ink: { DEFAULT: "#18161F", muted: "#6B6878" },
        paper: { DEFAULT: "#F7F6FA", card: "#FFFFFF", line: "#E8E5EF" },
        night: { DEFAULT: "#0E0C14", card: "#17151F", line: "#2A2735", muted: "#A19DB0" },
      },
      fontFamily: {
        sans: ["Inter_400Regular"],
        medium: ["Inter_500Medium"],
        semibold: ["Inter_600SemiBold"],
        bold: ["Inter_700Bold"],
      },
    },
  },
  plugins: [],
};
