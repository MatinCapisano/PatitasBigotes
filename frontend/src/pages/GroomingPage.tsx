import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { createTurnRequest } from "../services/turns-api";

const DAYS = [
  "Lunes",
  "Martes",
  "Miercoles",
  "Jueves",
  "Viernes",
  "Sabados (10am a 2pm y 4pm a 8pm)"
] as const;
const DOG_SIZES = ["Pequeno", "Mediano", "Grande"] as const;

export function GroomingPage() {
  const { isAuthenticated } = useAuth();
  const [day, setDay] = useState<(typeof DAYS)[number]>("Lunes");
  const [dogSize, setDogSize] = useState<(typeof DOG_SIZES)[number]>("Mediano");
  const [hourText, setHourText] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!isAuthenticated) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const notes = `Solicitud de peluqueria canina. Tamano perro: ${dogSize}. Dia: ${day}. Horario propuesto: ${hourText.trim()}.`;
      await createTurnRequest({
        scheduled_at: null,
        notes
      });
      setSuccess("Turno solicitado. Te confirmamos por WhatsApp.");
      setHourText("");
    } catch {
      setError("No se pudo solicitar el turno. Intenta nuevamente.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section>
      <h1 className="page-title">Peluqueria</h1>
      <p className="page-subtitle">
        Cuidado profesional para tu mascota: bano, corte y mantenimiento para que se vea y se sienta
        genial.
      </p>
      <div className="card">
        <h2>Pedir turno</h2>
        {!isAuthenticated ? (
          <div>
            <p>Para pedir turno tenes que iniciar sesion.</p>
            <Link className="btn btn-small" to="/login">
              Iniciar sesion
            </Link>
          </div>
        ) : (
          <form className="grooming-form" onSubmit={onSubmit}>
            <label>
              Tamano del perro
              <select
                className="input"
                value={dogSize}
                onChange={(event) => setDogSize(event.target.value as (typeof DOG_SIZES)[number])}
              >
                {DOG_SIZES.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Dia de la semana
              <select className="input" value={day} onChange={(event) => setDay(event.target.value as (typeof DAYS)[number])}>
                {DAYS.map((item) => (
                  <option key={item} value={item}>
                    {item}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Horario deseado
              <input
                className="input"
                value={hourText}
                onChange={(event) => setHourText(event.target.value)}
                placeholder="Ej: 16:30"
                required
              />
            </label>

            <p className="muted">
              Importante: espera confirmacion del turno por WhatsApp.
            </p>

            {error && <p className="error">{error}</p>}
            {success && <p className="success">{success}</p>}

            <button className="btn" type="submit" disabled={loading}>
              {loading ? "Enviando..." : "Solicitar turno"}
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
