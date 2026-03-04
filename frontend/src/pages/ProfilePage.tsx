import { FormEvent, useEffect, useState } from "react";
import type { MyOrder, MyProfile } from "../types";
import { getMyOrders, getMyProfile, updateMyProfile } from "../services/auth-api";

export function ProfilePage() {
  const [section, setSection] = useState<"summary" | "history" | "edit">("summary");
  const [profile, setProfile] = useState<MyProfile | null>(null);
  const [orders, setOrders] = useState<MyOrder[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  async function loadProfile() {
    setLoading(true);
    setError("");
    try {
      const data = await getMyProfile();
      setProfile(data);
      setFirstName(data.first_name || "");
      setLastName(data.last_name || "");
      setPhone(data.phone || "");
      setEmail(data.email || "");
    } catch {
      setError("No se pudo cargar tu perfil.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProfile();
  }, []);

  useEffect(() => {
    async function loadOrders() {
      if (section !== "history") return;
      setOrdersLoading(true);
      setOrdersError("");
      try {
        const data = await getMyOrders();
        setOrders(data);
      } catch {
        setOrdersError("No se pudo cargar tu historial de compras.");
      } finally {
        setOrdersLoading(false);
      }
    }
    void loadOrders();
  }, [section]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const previousEmail = profile.email;
      const result = await updateMyProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone: phone.trim(),
        email: email.trim()
      });
      setProfile(result.data);
      const verificationSent = Boolean((result.meta as Record<string, unknown>).verification_email_sent);
      if (verificationSent && previousEmail.trim().toLowerCase() !== email.trim().toLowerCase()) {
        setSuccess("Perfil actualizado. Como cambiaste el email, te enviamos una verificacion a tu nuevo correo.");
      } else {
        setSuccess("Perfil actualizado.");
      }
    } catch (apiError: unknown) {
      const detail =
        typeof apiError === "object" &&
        apiError !== null &&
        "response" in apiError &&
        typeof apiError.response === "object" &&
        apiError.response !== null &&
        "data" in apiError.response &&
        typeof apiError.response.data === "object" &&
        apiError.response.data !== null &&
        "detail" in apiError.response.data
          ? String(apiError.response.data.detail)
          : "No se pudo actualizar el perfil.";
      setError(detail);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">Mi cuenta</h1>
      <p className="page-subtitle">Administra tu cuenta desde el menu.</p>
      <div className="account-menu">
        <button
          className={`btn btn-small ${section === "summary" ? "" : "btn-ghost"}`}
          type="button"
          onClick={() => setSection("summary")}
        >
          Resumen
        </button>
        <button
          className={`btn btn-small ${section === "history" ? "" : "btn-ghost"}`}
          type="button"
          onClick={() => setSection("history")}
        >
          Historial de compras
        </button>
        <button
          className={`btn btn-small ${section === "edit" ? "" : "btn-ghost"}`}
          type="button"
          onClick={() => setSection("edit")}
        >
          Editar perfil
        </button>
      </div>
      {loading ? (
        <p>Cargando perfil...</p>
      ) : (
        <>
          {section === "summary" && profile && (
            <article className="card auth-wrap">
              <p><strong>Nombre:</strong> {profile.first_name} {profile.last_name}</p>
              <p><strong>Email:</strong> {profile.email}</p>
              <p><strong>Telefono:</strong> {profile.phone || "-"}</p>
              <p className="muted">
                Estado email: {profile.email_verified ? "Verificado" : "No verificado"}
              </p>
              <div className="checkout-actions">
                <button className="btn btn-small" type="button" onClick={() => setSection("edit")}>
                  Ir a editar perfil
                </button>
              </div>
            </article>
          )}

          {section === "edit" && (
            <article className="card auth-wrap">
              {profile && (
                <p className="muted">
                  Estado email: {profile.email_verified ? "Verificado" : "No verificado"}
                </p>
              )}
              <form className="auth-form" onSubmit={onSubmit}>
                <label>
                  Nombre
                  <input className="input" value={firstName} onChange={(event) => setFirstName(event.target.value)} required />
                </label>
                <label>
                  Apellido
                  <input className="input" value={lastName} onChange={(event) => setLastName(event.target.value)} required />
                </label>
                <label>
                  Telefono
                  <input className="input" value={phone} onChange={(event) => setPhone(event.target.value)} required />
                </label>
                <label>
                  Email
                  <input className="input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
                </label>
                <button className="btn" type="submit" disabled={saving}>
                  {saving ? "Guardando..." : "Guardar cambios"}
                </button>
              </form>
              {error && <p className="error">{error}</p>}
              {success && <p className="success">{success}</p>}
            </article>
          )}

          {section === "history" && (
            <div className="profile-orders">
              {ordersLoading && <p>Cargando historial...</p>}
              {ordersError && <p className="error">{ordersError}</p>}
              {!ordersLoading && !ordersError && orders.length === 0 && (
                <article className="card auth-wrap">
                  <p className="muted">Todavia no tenes compras registradas.</p>
                </article>
              )}
              {!ordersLoading && !ordersError && orders.map((order) => (
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
