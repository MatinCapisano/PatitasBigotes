import type { AdminSection } from "../types";

export function AdminSectionTabs(props: {
  adminSection: AdminSection;
  onSelect: (section: AdminSection) => void;
}) {
  const { adminSection, onSelect } = props;
  return (
    <div className="admin-section-tabs">
      <button className={`btn btn-small ${adminSection === "catalogo" ? "" : "btn-ghost"}`} type="button" onClick={() => onSelect("catalogo")}>
        Catalogo
      </button>
      <button className={`btn btn-small ${adminSection === "descuentos" ? "" : "btn-ghost"}`} type="button" onClick={() => onSelect("descuentos")}>
        Descuentos
      </button>
      <button className={`btn btn-small ${adminSection === "turnos" ? "" : "btn-ghost"}`} type="button" onClick={() => onSelect("turnos")}>
        Turnos
      </button>
      <button className={`btn btn-small ${adminSection === "ordenes" ? "" : "btn-ghost"}`} type="button" onClick={() => onSelect("ordenes")}>
        Ordenes
      </button>
      <button className={`btn btn-small ${adminSection === "pagos" ? "" : "btn-ghost"}`} type="button" onClick={() => onSelect("pagos")}>
        Pagos
      </button>
      <button className={`btn btn-small ${adminSection === "registrar_venta" ? "" : "btn-ghost"}`} type="button" onClick={() => onSelect("registrar_venta")}>
        Registrar venta
      </button>
      <button className={`btn btn-small ${adminSection === "registrar_pago" ? "" : "btn-ghost"}`} type="button" onClick={() => onSelect("registrar_pago")}>
        Registrar pago
      </button>
    </div>
  );
}
