export function AdminPage() {
  return (
    <section>
      <h1 className="page-title">Panel Admin</h1>
      <p className="page-subtitle">
        Base lista para conectar CRUD de productos, categorias, variantes, descuentos, turnos y pagos.
      </p>
      <div className="admin-grid">
        <article className="card">
          <h2>Catalogo</h2>
          <p>CRUD admin para productos/categorias/variantes.</p>
        </article>
        <article className="card">
          <h2>Ordenes y pagos</h2>
          <p>Pago manual, banco pendiente y seguimiento de estado.</p>
        </article>
        <article className="card">
          <h2>Turnos</h2>
          <p>Listado de pendientes y confirmacion/cancelacion manual.</p>
        </article>
      </div>
    </section>
  );
}
