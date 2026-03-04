import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getMyProfile, login as loginApi, logout as logoutApi } from "../services/auth-api";

type AuthContextValue = {
  isLoading: boolean;
  isAuthenticated: boolean;
  isAdmin: boolean;
  login: (email: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isLoading, setIsLoading] = useState(true);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    let mounted = true;
    async function bootstrapSession() {
      setIsLoading(true);
      try {
        const profile = await getMyProfile();
        if (!mounted) return;
        setIsAuthenticated(true);
        setIsAdmin(Boolean(profile.is_admin));
      } catch {
        if (!mounted) return;
        setIsAuthenticated(false);
        setIsAdmin(false);
      } finally {
        if (mounted) {
          setIsLoading(false);
        }
      }
    }

    void bootstrapSession();

    function handleUnauthorized() {
      if (!mounted) return;
      setIsAuthenticated(false);
      setIsAdmin(false);
      setIsLoading(false);
    }

    window.addEventListener("pb-auth-unauthorized", handleUnauthorized);
    return () => {
      mounted = false;
      window.removeEventListener("pb-auth-unauthorized", handleUnauthorized);
    };
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      isLoading,
      isAuthenticated,
      isAdmin,
      async login(email: string, password: string) {
        setIsLoading(true);
        try {
          await loginApi(email, password);
          const profile = await getMyProfile();
          const adminFlag = Boolean(profile.is_admin);
          setIsAuthenticated(true);
          setIsAdmin(adminFlag);
          return adminFlag;
        } finally {
          setIsLoading(false);
        }
      },
      async logout() {
        try {
          await logoutApi();
        } catch {
          // best effort: if backend logout fails, local auth state must still clear
        }
        setIsAuthenticated(false);
        setIsAdmin(false);
      }
    }),
    [isAuthenticated, isAdmin, isLoading]
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
