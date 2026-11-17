// Traduz o código de erro do Google Sign-In (Android) numa mensagem que ajuda a achar a causa.
// Códigos: https://developers.google.com/android/reference/com/google/android/gms/common/api/CommonStatusCodes
const MESSAGES: Record<string, string> = {
  "7": "Sem conexão com o Google. Confira a internet e tente de novo.",
  "10": "O Google não reconheceu este app. Confira o pacote e o SHA-1 do app Android no Firebase.",
  "12500": "O Google recusou o login. Confira a tela de consentimento e o e-mail de suporte no Firebase.",
  PLAY_SERVICES_NOT_AVAILABLE: "Atualize o Google Play Services do celular e tente de novo.",
};

export function googleSignInErrorMessage(code: unknown): string {
  const key = code === undefined || code === null ? "" : String(code).slice(0, 40);
  const base = MESSAGES[key] ?? "Não foi possível entrar com o Google. Confira a conexão e tente de novo.";
  return key ? `${base} (código ${key})` : base;
}
