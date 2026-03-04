import { useProfilePage } from "../features/profile";

export function ProfilePage() {
  const profilePage = useProfilePage();

  return (
    <section>
      <h1 className="page-title">Mi cuenta</h1>
      <p className="page-subtitle">Administra tu cuenta desde el menu.</p>
      <div className="account-menu">
        <button
          className={`btn btn-small ${profilePage.section === "summary" ? "" : "btn-ghost"}`}
          type="button"
          onClick={() => profilePage.setSection("summary")}
        >
          Resumen
        </button>
        <button
          className={`btn btn-small ${profilePage.section === "history" ? "" : "btn-ghost"}`}
          type="button"
          onClick={() => profilePage.setSection("history")}
        >
          Historial de compras
        </button>
        <button
          className={`btn btn-small ${profilePage.section === "edit" ? "" : "btn-ghost"}`}
          type="button"
          onClick={() => profilePage.setSection("edit")}
        >
          Editar perfil
        </button>
      </div>
      {profilePage.loading ? (
        <p>Cargando perfil...</p>
      ) : (
        <>
          {profilePage.section === "summary" && profilePage.profile && (
            <article className="card auth-wrap">
              <p><strong>Nombre:</strong> {profilePage.profile.first_name} {profilePage.profile.last_name}</p>
              <p><strong>Email:</strong> {profilePage.profile.email}</p>
              <p><strong>Telefono:</strong> {profilePage.profile.phone || "-"}</p>
              <p className="muted">
                Estado email: {profilePage.profile.email_verified ? "Verificado" : "No verificado"}
              </p>
              <div className="checkout-actions">
                <button className="btn btn-small" type="button" onClick={() => profilePage.setSection("edit")}>
                  Ir a editar perfil
                </button>
              </div>
            </article>
          )}

          {profilePage.section === "edit" && (
            <article className="card auth-wrap">
              {profilePage.profile && (
                <p className="muted">
                  Estado email: {profilePage.profile.email_verified ? "Verificado" : "No verificado"}
                </p>
              )}
              <form className="auth-form" onSubmit={profilePage.onSubmit}>
                <label>
                  Nombre
                  <input className="input" value={profilePage.firstName} onChange={(event) => profilePage.setFirstName(event.target.value)} required />
                </label>
                <label>
                  Apellido
                  <input className="input" value={profilePage.lastName} onChange={(event) => profilePage.setLastName(event.target.value)} required />
                </label>
                <label>
                  Telefono
                  <input className="input" value={profilePage.phone} onChange={(event) => profilePage.setPhone(event.target.value)} required />
                </label>
                <label>
                  Email
                  <input className="input" type="email" value={profilePage.email} onChange={(event) => profilePage.setEmail(event.target.value)} required />
                </label>
                <button className="btn" type="submit" disabled={profilePage.saving}>
                  {profilePage.saving ? "Guardando..." : "Guardar cambios"}
                </button>
              </form>
              {profilePage.error && <p className="error">{profilePage.error}</p>}
              {profilePage.success && <p className="success">{profilePage.success}</p>}
            </article>
          )}

          {profilePage.section === "history" && (
            <div className="profile-orders">
              {profilePage.ordersLoading && <p>Cargando historial...</p>}
              {profilePage.ordersError && <p className="error">{profilePage.ordersError}</p>}
              {!profilePage.ordersLoading && !profilePage.ordersError && profilePage.orders.length === 0 && (
                <article className="card auth-wrap">
                  <p className="muted">Todavia no tenes compras registradas.</p>
                </article>
              )}
              {!profilePage.ordersLoading && !profilePage.ordersError && profilePage.orders.map((order) => (
                <article className="card" key={order.id}>
                  <p><strong>Orden #{order.id}</strong> - {order.status}</p>
                  <p className="muted">Total: ${(order.total_amount / 100).toLocaleString("es-AR")} {order.currency}</p>
                  <div className="profile-order-items">
                    {order.items.map((item) => (
                      <div className="checkout-row" key={item.id}>
                        <div>
                          <strong>{item.product_name || `Producto #${item.product_id}`}</strong>
                          <p className="muted">Variante: {item.variant_label}</p>
                        </div>
                        <div>
                          <p>Cant: {item.quantity}</p>
                          <p>Unit: ${(item.unit_price / 100).toLocaleString("es-AR")}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}
