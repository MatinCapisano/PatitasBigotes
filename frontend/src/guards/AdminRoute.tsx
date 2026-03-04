import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function AdminRoute() {
  const { isLoading, isAuthenticated, isAdmin } = useAuth();
  if (isLoading) {
    return <p>Cargando sesion...</p>;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }
  return <Outlet />;
}
