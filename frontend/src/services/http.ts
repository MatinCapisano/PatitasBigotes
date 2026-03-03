import axios from "axios";
import { clearSession, getAccessToken } from "../lib/auth-storage";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

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
  (error) => {
    if (error?.response?.status === 401) {
      clearSession();
    }
    return Promise.reject(error);
  }
);
