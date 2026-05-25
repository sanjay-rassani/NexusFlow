import { api, clearTokens, storeTokens } from "./axios";

export interface User {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  role: "CUSTOMER" | "VENDOR" | "RIDER" | "ADMIN";
  is_email_verified: boolean;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  password_confirm: string;
  first_name: string;
  last_name: string;
  role?: string;
}

export async function login(payload: LoginPayload): Promise<User> {
  const { data } = await api.post("/auth/login/", payload);
  storeTokens(data.access, data.refresh);
  return data.user ?? (await fetchMe());
}

export async function register(payload: RegisterPayload): Promise<User> {
  const { data } = await api.post("/auth/register/", payload);
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get("/auth/me/");
  return data;
}

export async function logout(): Promise<void> {
  const refresh = localStorage.getItem("refresh_token");
  if (refresh) {
    try {
      await api.post("/auth/logout/", { refresh });
    } catch {
      // Ignore — we'll clear tokens regardless
    }
  }
  clearTokens();
}
