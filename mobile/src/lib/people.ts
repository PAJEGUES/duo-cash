import { PERSON_COLORS } from "@/constants/categories";
import type { Member } from "@/api/types";

/** A cor de cada pessoa segue a ordem de entrada no ambiente (dono = roxo, parceiro(a) = verde). */
export function colorFor(userId: string, members: Pick<Member, "user_id">[]): string {
  const i = members.findIndex((m) => m.user_id === userId);
  return PERSON_COLORS[(i < 0 ? members.length : i) % PERSON_COLORS.length];
}

export function initial(name: string): string {
  return ([...name.trim()][0] ?? "?").toUpperCase();
}

export function firstName(name: string): string {
  return name.trim().split(/\s+/)[0] ?? name;
}
