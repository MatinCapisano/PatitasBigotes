import axios from "axios";
import { clearSession, getAccessToken } from "../lib/auth-storage";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const fallbackBaseURL = (() => {
  if (baseURL.includes("127.0.0.1")) {
    return baseURL.replace("127.0.0.1", "localhost");
  }
  if (baseURL.includes("localhost")) {
    return baseURL.replace("localhost", "127.0.0.1");
  }
  return null;
})();

export const http = axios.create({
  baseURL,
  timeout: 10000
});

http.interceptors.request.use((config) => {
  const token = getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (response) => response,
  async (error) => {
    const config = error?.config as { baseURL?: string; headers?: Record<string, unknown> } | undefined;
    const alreadyRetried = config?.headers?.["X-Network-Retry"] === "1";
    if (
      error?.code === "ERR_NETWORK" &&
      fallbackBaseURL &&
      config &&
      !alreadyRetried
    ) {
      return http.request({
        ...config,
        baseURL: fallbackBaseURL,
        headers: {
          ...(config.headers ?? {}),
          "X-Network-Retry": "1"
        }
      });
    }
    if (error?.response?.status === 401) {
      clearSession();
    }
    return Promise.reject(error);
  }
);
