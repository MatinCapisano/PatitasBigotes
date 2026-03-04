import { FormEvent, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const admin = await login(email, password);
      navigate(admin ? "/admin" : "/profile");
    } catch (err: unknown) {
      const status = (err as { response?: { status?: number } })?.response?.status;
      if (status === 403) {
        setError("Email no verificado.");
      } else {
        setError("Credenciales invalidas.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="auth-wrap">
      <h1 className="page-title">Ingresar</h1>
      <form className="card auth-form" onSubmit={onSubmit}>
        <label>
          Email
          <input
            className="input"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </label>
        <label>
          Password
          <input
            className="input"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error && <p className="error">{error}</p>}
        <button className="btn" type="submit" disabled={loading}>
          {loading ? "Ingresando..." : "Entrar"}
        </button>
      </form>
    </section>
  );
}
