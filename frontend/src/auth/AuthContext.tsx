import { createContext, useContext, useMemo, useState } from "react";
import { clearSession, getAccessToken, isAdminSession, saveSession } from "../lib/auth-storage";
import { login as loginApi } from "../services/auth-api";

type AuthContextValue = {
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(Boolean(getAccessToken()));
  const [isAdmin, setIsAdmin] = useState(isAdminSession());

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      isAdmin,
      async login(email: string, password: string) {
        const session = await loginApi(email, password);
        // Simple decode to infer admin flag from access token payload.
        const payloadPart = session.access_token.split(".")[1] ?? "";
        let adminFlag = false;
        try {
          const decoded = JSON.parse(atob(payloadPart));
          adminFlag = Boolean(decoded?.is_admin);
        } catch {
          adminFlag = false;
        }
        saveSession(session.access_token, session.refresh_token, adminFlag);
        setIsAuthenticated(true);
        setIsAdmin(adminFlag);
      },
      logout() {
        clearSession();
        setIsAuthenticated(false);
        setIsAdmin(false);
      }
    }),
    [isAuthenticated, isAdmin]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return value;
}
