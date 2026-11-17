// Guarda o convite aberto antes do login, para retomar depois de entrar.
let pending: string | null = null;

export function setPendingInvite(token: string | null) {
  pending = token;
}

export function takePendingInvite(): string | null {
  const t = pending;
  pending = null;
  return t;
}
