import axios from "axios";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const http = axios.create({
  baseURL,
  timeout: 10000,
  withCredentials: true
});

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      window.dispatchEvent(new CustomEvent("pb-auth-unauthorized"));
    }
    return Promise.reject(error);
  }
);
