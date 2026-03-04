import { Link, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { cartCount } from "../lib/cart-storage";

export function Layout() {
  const location = useLocation();
  const { isAuthenticated, logout } = useAuth();
  const currentCartCount = cartCount();

  return (
    <div className="app-root">
      <header className="topbar">
        <div className="container topbar-inner">
          <Link className="brand" to="/home">
            <span className="brand-main">Patitas</span>
            <span className="brand-amp">&nbsp;y&nbsp;</span>
            <span className="brand-main">Bigotes</span>
          </Link>
          <nav className="nav">
            <Link to="/home">Tienda</Link>
            <Link to="/checkout">Carrito ({currentCartCount})</Link>
            {isAuthenticated && <Link to="/profile">Mi cuenta</Link>}
            {!isAuthenticated ? (
              <Link className="btn btn-small" to="/login">
                Ingresar
              </Link>
            ) : (
              <button className="btn btn-small btn-ghost" onClick={() => void logout()} type="button">
                Salir
              </button>
            )}
          </nav>
        </div>
        <div className="container">
          <nav className="menu-tabs" aria-label="Navegacion principal">
            <Link
              to="/home"
              className={location.pathname === "/home" ? "menu-tab menu-tab-active" : "menu-tab"}
            >
              Tienda
            </Link>
            <Link
              to="/peluqueria"
              className={location.pathname === "/peluqueria" ? "menu-tab menu-tab-active" : "menu-tab"}
            >
              Peluqueria
            </Link>
            <Link
              to="/contacto"
              className={location.pathname === "/contacto" ? "menu-tab menu-tab-active" : "menu-tab"}
            >
              Contacto
            </Link>
          </nav>
        </div>
      </header>
      <main className="container page">
        <Outlet />
      </main>
    </div>
  );
}
