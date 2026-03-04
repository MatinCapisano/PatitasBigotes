import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const AUTH_ROUTES_WITH_LOCAL_HANDLING = ["/auth/login", "/auth/logout", "/auth/refresh", "/auth/me"];

function shouldSkipUnauthorizedBroadcast(url: string | undefined): boolean {
  if (!url) return false;
  const normalized = String(url).split("?")[0];
  return AUTH_ROUTES_WITH_LOCAL_HANDLING.some(
    (route) => normalized === route || normalized.endsWith(route)
  );
}

export const http = axios.create({
  baseURL,
  timeout: 10000,
  withCredentials: true
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl =
      (error?.config as { url?: string } | undefined)?.url;
    if (error?.response?.status === 401 && !shouldSkipUnauthorizedBroadcast(requestUrl)) {
      window.dispatchEvent(new CustomEvent("pb-auth-unauthorized"));
    }
    return Promise.reject(error);
  }
);
