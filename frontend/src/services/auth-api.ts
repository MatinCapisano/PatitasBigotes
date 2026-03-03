import { http } from "./http";
import type { ApiEnvelope, LoginResponse } from "../types";

export async function login(email: string, password: string) {
  const response = await http.post<ApiEnvelope<LoginResponse>>("/auth/login", {
    email,
    password
  });
  return response.data.data;
}
