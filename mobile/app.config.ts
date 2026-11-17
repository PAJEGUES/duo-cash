import type { ExpoConfig } from "expo/config";

// A URL do servidor pode ser trocada dentro do app (tela de login > Servidor).
// Aqui fica só o valor padrão usado no build.
const apiUrl = process.env.EXPO_PUBLIC_API_URL ?? "";

const config: ExpoConfig = {
  name: "DuoCash",
  slug: "duo-cash",
  version: "0.1.2",
  orientation: "portrait",
  icon: "./assets/icon.png",
  scheme: "duocash",
  userInterfaceStyle: "automatic",
  android: {
    package: "com.pajegues.duocash",
    versionCode: 3,
    adaptiveIcon: {
      backgroundColor: "#6D4FC2",
      foregroundImage: "./assets/android-icon-foreground.png",
      backgroundImage: "./assets/android-icon-background.png",
      monochromeImage: "./assets/android-icon-monochrome.png",
    },
    predictiveBackGestureEnabled: false,
    allowBackup: false,
    blockedPermissions: [
      "android.permission.RECORD_AUDIO",
      "android.permission.READ_EXTERNAL_STORAGE",
      "android.permission.WRITE_EXTERNAL_STORAGE",
      "android.permission.SYSTEM_ALERT_WINDOW",
    ],
  },
  plugins: [
    "expo-router",
    "expo-secure-store",
    "expo-font",
    "@react-native-community/datetimepicker",
    "@react-native-google-signin/google-signin",
    "./plugins/withReleaseSigning",
    [
      "expo-camera",
      {
        cameraPermission: "O DuoCash usa a câmera só para ler o QR Code do convite.",
        microphonePermission: false,
        recordAudioAndroid: false,
      },
    ],
    [
      "expo-build-properties",
      {
        android: {
          usesCleartextTraffic: false,
        },
      },
    ],
  ],
  experiments: {
    typedRoutes: true,
  },
  extra: {
    apiUrl,
  },
};

export default config;
