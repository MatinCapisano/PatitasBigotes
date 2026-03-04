import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { DAYS, DOG_SIZES, useGroomingPage } from "../features/turns";

export function GroomingPage() {
  const { isLoading: authLoading, isAuthenticated } = useAuth();
  const grooming = useGroomingPage({ authLoading, isAuthenticated });

  return (
    <section>
      <h1 className="page-title">Peluqueria</h1>
      <p className="page-subtitle">
        Cuidado profesional para tu mascota: bano, corte y mantenimiento para que se vea y se sienta
        genial.
      </p>
      <div className="card">
        <h2>Pedir turno</h2>
        {authLoading ? (
          <p className="muted">Verificando sesion...</p>
        ) : !isAuthenticated ? (
          <div>
            <p>Para pedir turno tenes que iniciar sesion.</p>
            <Link className="btn btn-small" to="/login">
              Iniciar sesion
            </Link>
          </div>
        ) : (
          <form className="grooming-form" onSubmit={grooming.onSubmit}>
            <label>
              Tamano del perro
              <select
                className="input"
                value={grooming.dogSize}
                onChange={(event) => grooming.setDogSize(event.target.value as (typeof DOG_SIZES)[number])}
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
              <select className="input" value={grooming.day} onChange={(event) => grooming.setDay(event.target.value as (typeof DAYS)[number])}>
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
                value={grooming.hourText}
                onChange={(event) => grooming.setHourText(event.target.value)}
                placeholder="Ej: 16:30"
                required
              />
            </label>

            <p className="muted">
              Importante: espera confirmacion del turno por WhatsApp.
            </p>

            {grooming.error && <p className="error">{grooming.error}</p>}
            {grooming.success && <p className="success">{grooming.success}</p>}

            <button className="btn" type="submit" disabled={grooming.loading}>
              {grooming.loading ? "Enviando..." : "Solicitar turno"}
            </button>
          </form>
        )}
      </div>
    </section>
  );
}
