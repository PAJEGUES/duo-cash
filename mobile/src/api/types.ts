export type Role = "OWNER" | "EDITOR" | "VIEWER";

export type User = { id: string; email: string; display_name: string; avatar_url: string | null };

export type Member = {
  user_id: string;
  display_name: string;
  email: string;
  avatar_url: string | null;
  role: Role;
  joined_at: string;
};

export type Workspace = {
  id: string;
  name: string;
  icon: string;
  currency: string;
  role: Role;
  owner_id: string;
  created_at: string;
  archived_at: string | null;
  members: Member[];
  month_total_cents: number;
};

export type Expense = {
  id: string;
  workspace_id: string;
  author: { id: string; display_name: string; avatar_url: string | null };
  amount_cents: number;
  spent_at: string;
  description: string;
  category: string;
  icon_key: string | null;
  created_at: string;
  updated_at: string;
};

export type ExpensePage = {
  items: Expense[];
  total_count: number;
  total_cents: number;
  next_offset: number | null;
};

export type ExpenseFilters = {
  q?: string;
  category?: string[];
  author_id?: string;
  date_from?: string;
  date_to?: string;
  amount_min?: number;
  amount_max?: number;
};

export type Summary = {
  month: string;
  total_cents: number;
  count: number;
  by_category: { category: string; total_cents: number; count: number }[];
  by_author: { user_id: string; display_name: string; total_cents: number; count: number }[];
  evolution: { month: string; total_cents: number }[];
};

export type CreatedInvite = {
  id: string;
  token: string;
  role: Role;
  expires_at: string;
  app_url: string;
  share_url: string;
};

export type PendingInvite = { id: string; role: Role; created_at: string; expires_at: string; created_by: string };

export type InvitePreview = {
  workspace_name: string;
  workspace_icon: string;
  role: Role;
  invited_by: string;
  expires_at: string;
};

export type AuthResponse = { access_token: string; refresh_token: string; user: User };

export type ServerConfig = { google_web_client_id: string; invite_ttl_minutes: number };
