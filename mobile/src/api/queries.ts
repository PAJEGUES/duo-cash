import { useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "./client";
import type {
  CreatedInvite, Expense, ExpenseFilters, ExpensePage, InvitePreview, PendingInvite, Role, Summary, Workspace,
} from "./types";
import type { ExpenseInput } from "@/lib/validation";

const PAGE = 50;

export const keys = {
  workspaces: (month: string) => ["workspaces", month] as const,
  workspace: (id: string) => ["workspace", id] as const,
  expenses: (id: string, f: ExpenseFilters) => ["expenses", id, f] as const,
  summary: (id: string, month: string) => ["summary", id, month] as const,
  invites: (id: string) => ["invites", id] as const,
};

function qs(params: Record<string, string | number | undefined>) {
  const parts = Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== "")
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`);
  return parts.length ? `?${parts.join("&")}` : "";
}

const enc = encodeURIComponent;

export function useWorkspaces(month: string) {
  return useQuery({
    queryKey: keys.workspaces(month),
    queryFn: () => api<{ items: Workspace[] }>(`/workspaces${qs({ month, include_archived: 1 })}`).then((r) => r.items),
  });
}

export function useWorkspace(id: string | undefined) {
  return useQuery({
    queryKey: keys.workspace(id ?? ""),
    queryFn: () => api<Workspace>(`/workspaces/${enc(id!)}`),
    enabled: !!id,
  });
}

export function useExpenses(workspaceId: string | undefined, filters: ExpenseFilters) {
  return useInfiniteQuery({
    queryKey: keys.expenses(workspaceId ?? "", filters),
    enabled: !!workspaceId,
    initialPageParam: 0,
    getNextPageParam: (last: ExpensePage) => last.next_offset ?? undefined,
    queryFn: ({ pageParam }) =>
      api<ExpensePage>(
        `/workspaces/${enc(workspaceId!)}/expenses${qs({
          ...filters,
          category: filters.category?.join(","),
          limit: PAGE,
          offset: pageParam,
        })}`,
      ),
  });
}

export function useSummary(workspaceId: string | undefined, month: string) {
  return useQuery({
    queryKey: keys.summary(workspaceId ?? "", month),
    queryFn: () => api<Summary>(`/workspaces/${enc(workspaceId!)}/summary${qs({ month })}`),
    enabled: !!workspaceId,
  });
}

export function usePendingInvites(workspaceId: string | undefined, enabled: boolean) {
  return useQuery({
    queryKey: keys.invites(workspaceId ?? ""),
    queryFn: () => api<{ items: PendingInvite[] }>(`/workspaces/${enc(workspaceId!)}/invites`).then((r) => r.items),
    enabled: !!workspaceId && enabled,
  });
}

/** Qualquer mudança em gastos ou ambientes invalida as listas e resumos. */
function useInvalidateAll() {
  const qc = useQueryClient();
  return () => qc.invalidateQueries();
}

export function useSaveExpense(workspaceId: string) {
  const invalidate = useInvalidateAll();
  return useMutation({
    // Retry seguro: a mesma Idempotency-Key é reenviada em cada tentativa (RNF09).
    retry: 3,
    mutationFn: ({ input, id, idempotencyKey }: { input: ExpenseInput; id?: string; idempotencyKey: string }) =>
      id
        ? api<Expense>(`/expenses/${enc(id)}`, { method: "PATCH", body: input })
        : api<Expense>(`/workspaces/${enc(workspaceId)}/expenses`, {
            method: "POST",
            body: input,
            headers: { "Idempotency-Key": idempotencyKey },
          }),
    onSuccess: invalidate,
  });
}

export function useDeleteExpense() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/expenses/${enc(id)}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}

export function useCreateWorkspace() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (body: { name: string; icon: string }) => api<Workspace>("/workspaces", { method: "POST", body }),
    onSuccess: invalidate,
  });
}

export function useUpdateWorkspace(id: string) {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (body: { name?: string; icon?: string; archived?: boolean }) =>
      api<Workspace>(`/workspaces/${enc(id)}`, { method: "PATCH", body }),
    onSuccess: invalidate,
  });
}

export function useDeleteWorkspace() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (id: string) => api<void>(`/workspaces/${enc(id)}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}

export function useRemoveMember(workspaceId: string) {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (userId: string) =>
      api<void>(`/workspaces/${enc(workspaceId)}/members/${enc(userId)}`, { method: "DELETE" }),
    onSuccess: invalidate,
  });
}

export function useLeaveWorkspace() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (workspaceId: string) => api<void>(`/workspaces/${enc(workspaceId)}/leave`, { method: "POST" }),
    onSuccess: invalidate,
  });
}

export function useCreateInvite(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (role: Exclude<Role, "OWNER">) =>
      api<CreatedInvite>(`/workspaces/${enc(workspaceId)}/invites`, { method: "POST", body: { role } }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.invites(workspaceId) }),
  });
}

export function useCancelInvite(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (inviteId: string) => api<void>(`/invites/${enc(inviteId)}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.invites(workspaceId) }),
  });
}

export function useInvitePreview(token: string | undefined) {
  return useQuery({
    queryKey: ["invite", token],
    queryFn: () => api<InvitePreview>(`/invites/${enc(token!)}`),
    enabled: !!token,
    retry: false,
  });
}

export function useAcceptInvite() {
  const invalidate = useInvalidateAll();
  return useMutation({
    mutationFn: (token: string) => api<{ workspace: Workspace }>(`/invites/${enc(token)}/accept`, { method: "POST" }),
    onSuccess: invalidate,
  });
}

