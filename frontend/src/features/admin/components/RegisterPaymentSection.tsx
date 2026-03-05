import type { AdminOrder } from "../../../services/admin-orders-api";
import type { AdminSearchUser } from "../../../services/admin-sales-api";

export function RegisterPaymentSection(props: {
  selectedUser: AdminSearchUser | null;
  onClearSelectedUser: () => void;
  showUserSearch: boolean;
  openUserSearchModal: () => void;
  closeUserSearchModal: () => void;
  searchFirstName: string;
  setSearchFirstName: (value: string) => void;
  searchLastName: string;
  setSearchLastName: (value: string) => void;
  searchEmail: string;
  setSearchEmail: (value: string) => void;
  searchDni: string;
  setSearchDni: (value: string) => void;
  searchPhone: string;
  setSearchPhone: (value: string) => void;
  searchLoading: boolean;
  searchError: string;
  searchResults: AdminSearchUser[];
  pendingSelectedUser: AdminSearchUser | null;
  onTogglePendingUser: (user: AdminSearchUser, checked: boolean) => void;
  onConfirmPendingUser: () => void;
  orders: AdminOrder[];
  ordersLoading: boolean;
  ordersError: string;
  selectedOrderId: number | null;
  setSelectedOrderId: (value: number) => void;
  selectedOrder: AdminOrder | null;
  method: "cash" | "bank_transfer";
  setMethod: (value: "cash" | "bank_transfer") => void;
  paidAmount: string;
  setPaidAmount: (value: string) => void;
  changeAmount: string;
  setChangeAmount: (value: string) => void;
  paymentRef: string;
  setPaymentRef: (value: string) => void;
  saving: boolean;
  error: string;
  success: string;
  showConfirmModal: boolean;
  setShowConfirmModal: (value: boolean) => void;
  onOpenConfirm: () => void;
  onConfirmPayment: () => Promise<void>;
  formatArs: (cents: number | null) => string;
}) {
  const {
    selectedUser,
    onClearSelectedUser,
    showUserSearch,
    openUserSearchModal,
    closeUserSearchModal,
    searchFirstName,
    setSearchFirstName,
    searchLastName,
    setSearchLastName,
    searchEmail,
    setSearchEmail,
    searchDni,
    setSearchDni,
    searchPhone,
    setSearchPhone,
    searchLoading,
    searchError,
    searchResults,
    pendingSelectedUser,
    onTogglePendingUser,
    onConfirmPendingUser,
    orders,
    ordersLoading,
    ordersError,
    selectedOrderId,
    setSelectedOrderId,
    selectedOrder,
    method,
    setMethod,
    paidAmount,
    setPaidAmount,
    changeAmount,
    setChangeAmount,
    paymentRef,
    setPaymentRef,
    saving,
    error,
    success,
    showConfirmModal,
    setShowConfirmModal,
    onOpenConfirm,
    onConfirmPayment,
    formatArs
  } = props;

  return (
    <article className="card admin-orders-section">
      <h2>Registrar pago</h2>
      <p className="muted">Selecciona cliente, elige una orden submitted y confirma el pago con doble chequeo.</p>

      <section className="admin-sales-block">
        <h3>Cliente</h3>
        <div className="admin-inline-actions">
          <button className="btn btn-small btn-ghost" type="button" onClick={openUserSearchModal}>
            Buscar usuario existente
          </button>
          {selectedUser && (
            <button className="btn btn-small btn-ghost" type="button" onClick={onClearSelectedUser}>
              Quitar usuario seleccionado
            </button>
          )}
        </div>
        {selectedUser ? (
          <p className="muted">
            Seleccionado: #{selectedUser.id} - {selectedUser.first_name} {selectedUser.last_name} ({selectedUser.email})
          </p>
        ) : (
          <p className="muted">Todavia no seleccionaste un usuario.</p>
        )}
      </section>

      <section className="admin-sales-block">
        <h3>Ordenes submitted del cliente</h3>
        {ordersLoading ? (
          <p className="muted">Cargando ordenes...</p>
        ) : orders.length === 0 ? (
          <p className="muted">No hay ordenes submitted para este cliente.</p>
        ) : (
          <div className="admin-scroll-list admin-search-results-list">
            {orders.map((order) => (
              <label className="admin-user-search-row" key={order.id}>
                <span className="admin-discount-product-check">
                  <input
                    type="checkbox"
                    checked={selectedOrderId === order.id}
                    onChange={(event) => {
                      if (event.target.checked) setSelectedOrderId(order.id);
                    }}
                  />
                  <span>Orden #{order.id}</span>
                </span>
                <span className="muted">Estado: {order.status}</span>
                <span className="muted">Total: {formatArs(order.total_amount)}</span>
              </label>
            ))}
          </div>
        )}
        {ordersError && <p className="error">{ordersError}</p>}
      </section>

      <section className="admin-sales-block">
        <h3>Pago</h3>
        <div className="admin-sales-fields">
          <label>
            Metodo
            <select className="input" value={method} onChange={(e) => setMethod(e.target.value as "cash" | "bank_transfer")}>
              <option value="cash">Efectivo</option>
              <option value="bank_transfer">Transferencia</option>
            </select>
          </label>
          <label>
            Monto pagado (ARS)
            <input
              className="input"
              type="text"
              inputMode="numeric"
              placeholder="Ej: 19000 o 19.000"
              value={paidAmount}
              onChange={(e) => setPaidAmount(e.target.value)}
            />
          </label>
          {method === "cash" && (
            <label>
              Vuelto (ARS)
              <input
                className="input"
                type="text"
                inputMode="numeric"
                placeholder="Ej: 500"
                value={changeAmount}
                onChange={(e) => setChangeAmount(e.target.value)}
              />
            </label>
          )}
          <label>
            Referencia de pago (nro. transaccion/comprobante) {method === "bank_transfer" ? "(obligatoria)" : "(opcional)"}
            <input className="input" value={paymentRef} onChange={(e) => setPaymentRef(e.target.value)} />
          </label>
        </div>
        <div className="admin-inline-actions">
          <button className="btn" type="button" onClick={onOpenConfirm} disabled={saving}>
            Confirmar pago
          </button>
        </div>
      </section>

      {error && <p className="error">{error}</p>}
      {success && <p className="success">{success}</p>}

      {showUserSearch && (
        <div className="admin-modal-overlay" role="dialog" aria-modal="true">
          <div className="card admin-modal">
            <div className="admin-modal-header">
              <h3>Buscar usuario existente</h3>
              <button className="btn btn-small btn-ghost" type="button" onClick={closeUserSearchModal}>
                X
              </button>
            </div>
            <div className="admin-search-toolbar">
              <label className="admin-search-field">
                Nombre
                <input className="input" value={searchFirstName} onChange={(e) => setSearchFirstName(e.target.value)} />
              </label>
              <label className="admin-search-field">
                Apellido
                <input className="input" value={searchLastName} onChange={(e) => setSearchLastName(e.target.value)} />
              </label>
              <label className="admin-search-field">
                Email
                <input className="input" value={searchEmail} onChange={(e) => setSearchEmail(e.target.value)} />
              </label>
              <label className="admin-search-field">
                DNI
                <input className="input" value={searchDni} onChange={(e) => setSearchDni(e.target.value)} />
              </label>
              <label className="admin-search-field">
                Telefono
                <input className="input" value={searchPhone} onChange={(e) => setSearchPhone(e.target.value)} />
              </label>
            </div>
            {searchLoading && <p className="muted">Buscando...</p>}
            {searchError && <p className="error">{searchError}</p>}
            <div className="admin-scroll-list admin-search-results-list">
              {searchResults.map((user) => (
                <div className="admin-user-search-row" key={user.id}>
                  <label className="admin-discount-product-check">
                    <input
                      type="checkbox"
                      checked={pendingSelectedUser?.id === user.id}
                      onChange={(event) => onTogglePendingUser(user, event.target.checked)}
                    />
                    <span>#{user.id} {user.first_name} {user.last_name}</span>
                  </label>
                  <p className="muted">Email: {user.email}</p>
                  <p className="muted">DNI: {user.dni || "-"} | Tel: {user.phone || "-"}</p>
                </div>
              ))}
            </div>
            <p className="muted">
              {pendingSelectedUser
                ? `Seleccion temporal: #${pendingSelectedUser.id} - ${pendingSelectedUser.first_name} ${pendingSelectedUser.last_name}`
                : "Seleccion temporal: -"}
            </p>
            <div className="admin-inline-actions">
              <button className="btn btn-small" type="button" onClick={onConfirmPendingUser} disabled={!pendingSelectedUser}>
                Seleccionar
              </button>
            </div>
          </div>
        </div>
      )}

      {showConfirmModal && selectedOrder && selectedUser && (
        <div className="admin-modal-overlay" role="dialog" aria-modal="true">
          <div className="card admin-modal">
            <div className="admin-modal-header">
              <h3>Confirmar pago</h3>
              <button className="btn btn-small btn-ghost" type="button" onClick={() => setShowConfirmModal(false)}>
                X
              </button>
            </div>
            <p className="muted">
              Orden #{selectedOrder.id} | Cliente: {selectedUser.first_name} {selectedUser.last_name}
            </p>
            <p className="muted">Total orden: {formatArs(selectedOrder.total_amount)}</p>
            <p className="muted">Metodo: {method === "cash" ? "Efectivo" : "Transferencia"}</p>
            <p className="muted">Monto pagado: {paidAmount}</p>
            {method === "cash" && <p className="muted">Vuelto: {changeAmount}</p>}
            {paymentRef.trim() && <p className="muted">Referencia: {paymentRef.trim()}</p>}
            <div className="admin-inline-actions">
              <button className="btn" type="button" onClick={() => void onConfirmPayment()} disabled={saving}>
                {saving ? "Guardando..." : "Confirmar definitivamente"}
              </button>
            </div>
          </div>
        </div>
      )}
    </article>
  );
}
