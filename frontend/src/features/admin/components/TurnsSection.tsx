import type { AdminTurn } from "../services";

export function TurnsSection(props: {
  turns: AdminTurn[];
  turnsError: string;
  turnsFilter: "all" | "pending" | "confirmed" | "cancelled";
  setTurnsFilter: (value: "all" | "pending" | "confirmed" | "cancelled") => void;
  loadTurns: () => Promise<void>;
  onUpdateTurnStatus: (turnId: number, status: "confirmed" | "cancelled") => Promise<void>;
}) {
  const { turns, turnsError, turnsFilter, setTurnsFilter, loadTurns, onUpdateTurnStatus } = props;

  return (
    <article className="card admin-orders-section">
      <h2>Admin Turnos</h2>
      <div className="admin-inline-actions">
        <select
          className="input"
          value={turnsFilter}
          onChange={(e) => setTurnsFilter(e.target.value as "all" | "pending" | "confirmed" | "cancelled")}
        >
          <option value="all">Todos</option>
          <option value="pending">Pendientes</option>
          <option value="confirmed">Confirmados</option>
          <option value="cancelled">Cancelados</option>
        </select>
        <button className="btn btn-small" type="button" onClick={() => void loadTurns()}>
          Refrescar
        </button>
      </div>
      {turnsError && <p className="error">{turnsError}</p>}
      {turns.length === 0 ? (
        <p className="muted">No hay turnos para mostrar.</p>
      ) : (
        <div className="admin-variants-grid">
          {turns.map((turn) => (
            <div className="admin-variant-row" key={turn.id}>
              <p>
                <strong>#{turn.id}</strong> {turn.customer.first_name || ""} {turn.customer.last_name || ""}
              </p>
              <p className="muted">Telefono: {turn.customer.phone || "-"}</p>
              <p className="muted">Horario: {turn.notes || turn.scheduled_at || "-"}</p>
              <p className="muted">Estado: {turn.status}</p>
              {turn.status === "pending" && (
                <div className="admin-product-actions">
                  <button className="btn btn-small" type="button" onClick={() => void onUpdateTurnStatus(turn.id, "confirmed")}>
                    Confirmar
                  </button>
                  <button className="btn btn-small btn-danger" type="button" onClick={() => void onUpdateTurnStatus(turn.id, "cancelled")}>
                    Cancelar
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </article>
  );
}
