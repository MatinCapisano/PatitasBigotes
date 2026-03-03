import { Link, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function Layout() {
  const { isAuthenticated, isAdmin, logout } = useAuth();

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="container topbar-inner">
          <Link className="brand" to="/">
            Patitas & Bigotes
          </Link>
          <nav className="nav">
            <Link to="/">Tienda</Link>
            {isAuthenticated && <Link to="/profile">Mi cuenta</Link>}
            {isAdmin && <Link to="/admin">Admin</Link>}
            {!isAuthenticated ? (
              <Link className="btn btn-small" to="/login">
                Ingresar
              </Link>
            ) : (
              <button className="btn btn-small btn-ghost" onClick={logout} type="button">
                Salir
              </button>
            )}
          </nav>
        </div>
      </header>
      <main className="container page">
        <Outlet />
      </main>
    </div>
  );
}
