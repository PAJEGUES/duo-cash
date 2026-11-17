import "../../global.css";

import { Inter_400Regular, Inter_500Medium, Inter_600SemiBold, Inter_700Bold, useFonts } from "@expo-google-fonts/inter";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SplashScreen, Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { ApiError } from "@/api/client";
import { AuthProvider, useAuth } from "@/auth/AuthProvider";
import { usePalette } from "@/constants/theme";
import { CurrentWorkspaceProvider } from "@/lib/currentWorkspace";

SplashScreen.preventAutoHideAsync().catch(() => undefined);

function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 30_000,
        gcTime: 24 * 60 * 60_000,
        // Internet ruim: tenta de novo, mas não insiste em erros de permissão/validação.
        retry: (count, err) => count < 3 && (!(err instanceof ApiError) || err.status === 0 || err.status >= 500),
        retryDelay: (n) => Math.min(1000 * 2 ** n, 8000),
      },
    },
  });
}

function RootStack() {
  const { status } = useAuth();
  const p = usePalette();

  useEffect(() => {
    if (status !== "loading") SplashScreen.hideAsync().catch(() => undefined);
  }, [status]);

  if (status === "loading") return null;
  const signedIn = status === "signedIn";

  return (
    <>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: p.bg }, animation: "slide_from_right" }}>
        <Stack.Protected guard={!signedIn}>
          <Stack.Screen name="login" />
        </Stack.Protected>
        <Stack.Protected guard={signedIn}>
          <Stack.Screen name="(tabs)" />
          <Stack.Screen name="gasto" options={{ presentation: "modal", animation: "slide_from_bottom" }} />
          <Stack.Screen name="scan" options={{ animation: "fade" }} />
          <Stack.Screen name="conta" />
          <Stack.Screen name="ambiente/novo" options={{ presentation: "modal", animation: "slide_from_bottom" }} />
          <Stack.Screen name="ambiente/[id]" />
        </Stack.Protected>
        {/* O link do convite funciona logado ou não: se não estiver, a tela pede login primeiro. */}
        <Stack.Screen name="join/[token]" />
      </Stack>
    </>
  );
}

export default function RootLayout() {
  const [queryClient] = useState(makeQueryClient);
  const [fontsLoaded] = useFonts({ Inter_400Regular, Inter_500Medium, Inter_600SemiBold, Inter_700Bold });
  if (!fontsLoaded) return null;

  return (
    <SafeAreaProvider>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <CurrentWorkspaceProvider>
            <RootStack />
          </CurrentWorkspaceProvider>
        </AuthProvider>
      </QueryClientProvider>
    </SafeAreaProvider>
  );
}
