const ACCESS_KEY = "pb_access_token";
const REFRESH_KEY = "pb_refresh_token";
const ADMIN_KEY = "pb_is_admin";

export function saveSession(accessToken: string, refreshToken: string, isAdmin: boolean): void {
  localStorage.setItem(ACCESS_KEY, accessToken);
  localStorage.setItem(REFRESH_KEY, refreshToken);
  localStorage.setItem(ADMIN_KEY, isAdmin ? "1" : "0");
}

export function clearSession(): void {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(ADMIN_KEY);
}

export function getAccessToken(): string {
  return localStorage.getItem(ACCESS_KEY) ?? "";
}

export function getRefreshToken(): string {
  return localStorage.getItem(REFRESH_KEY) ?? "";
}

export function isAdminSession(): boolean {
  return localStorage.getItem(ADMIN_KEY) === "1";
}
