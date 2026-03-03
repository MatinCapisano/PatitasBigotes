import { FormEvent, useEffect, useState } from "react";
import type { MyProfile } from "../types";
import { getMyProfile, updateMyProfile } from "../services/auth-api";

export function ProfilePage() {
  const [profile, setProfile] = useState<MyProfile | null>(null);
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
      <p className="page-subtitle">Edita tus datos personales. Si cambias email, se pedira verificacion.</p>
      {loading ? (
        <p>Cargando perfil...</p>
      ) : (
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
    </section>
  );
}
