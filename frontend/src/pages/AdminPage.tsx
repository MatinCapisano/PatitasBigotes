import { FormEvent, useEffect, useMemo, useState } from "react";
import {
  type AdminCategory,
  type AdminProduct,
  type AdminVariant,
  createAdminProduct,
  deleteAdminProduct,
  listAdminCategories,
  listAdminProducts,
  listProductVariants,
  patchAdminProduct,
  patchAdminVariant
} from "../services/admin-catalog-api";
import {
  adminMarkOrderPaid,
  createManualSubmittedOrder,
  getAdminOrder,
  listAdminOrderPayments,
  type AdminOrder,
  type AdminPayment
} from "../services/admin-orders-api";
import { listAdminTurns, type AdminTurn, updateAdminTurnStatus } from "../services/turns-api";

function formatArs(cents: number | null) {
  if (cents === null) return "-";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0
  }).format(cents / 100);
}

export function AdminPage() {
  const [adminSection, setAdminSection] = useState<"catalogo" | "turnos" | "ordenes" | "pagos">("catalogo");
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [variantsByProduct, setVariantsByProduct] = useState<Record<number, AdminVariant[]>>({});
  const [editingProductId, setEditingProductId] = useState<number | null>(null);
  const [editName, setEditName] = useState("");
  const [editDescription, setEditDescription] = useState("");
  const [editImgUrl, setEditImgUrl] = useState("");
  const [editCategory, setEditCategory] = useState("");
  const [editActive, setEditActive] = useState(true);
  const [editingVariantId, setEditingVariantId] = useState<number | null>(null);
  const [editVariantSku, setEditVariantSku] = useState("");
  const [editVariantSize, setEditVariantSize] = useState("");
  const [editVariantColor, setEditVariantColor] = useState("");
  const [editVariantImgUrl, setEditVariantImgUrl] = useState("");
  const [editVariantStock, setEditVariantStock] = useState("0");
  const [editVariantActive, setEditVariantActive] = useState(true);
  const [enableVariantPriceEdit, setEnableVariantPriceEdit] = useState(false);
  const [editVariantPrice, setEditVariantPrice] = useState("0");
  const [editVariantOriginalPrice, setEditVariantOriginalPrice] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [newName, setNewName] = useState("");
  const [newDescription, setNewDescription] = useState("");
  const [newImgUrl, setNewImgUrl] = useState("");
  const [newCategory, setNewCategory] = useState("");
  const [savingNew, setSavingNew] = useState(false);
  const [orderError, setOrderError] = useState("");
  const [orderSuccess, setOrderSuccess] = useState("");
  const [orderLookupId, setOrderLookupId] = useState("");
  const [selectedOrder, setSelectedOrder] = useState<AdminOrder | null>(null);
  const [orderPayments, setOrderPayments] = useState<AdminPayment[]>([]);
  const [manualEmail, setManualEmail] = useState("");
  const [manualFirstName, setManualFirstName] = useState("");
  const [manualLastName, setManualLastName] = useState("");
  const [manualPhone, setManualPhone] = useState("");
  const [manualVariantId, setManualVariantId] = useState("");
  const [manualQuantity, setManualQuantity] = useState("1");
  const [manualItems, setManualItems] = useState<Array<{ variant_id: number; quantity: number; label: string }>>([]);
  const [manualPayRef, setManualPayRef] = useState("");
  const [manualPayAmount, setManualPayAmount] = useState("");
  const [turns, setTurns] = useState<AdminTurn[]>([]);
  const [turnsFilter, setTurnsFilter] = useState<"all" | "pending" | "confirmed" | "cancelled">("all");
  const [turnsError, setTurnsError] = useState("");

  const hasCategories = categories.length > 0;

  async function loadAll() {
    setLoading(true);
    setError("");
    try {
      const [productList, categoryList] = await Promise.all([listAdminProducts(), listAdminCategories()]);
      setProducts(productList);
      setCategories(categoryList);
      if (!newCategory && categoryList[0]?.name) {
        setNewCategory(categoryList[0].name);
      }

      const variantsEntries = await Promise.all(
        productList.map(async (product) => {
          const variants = await listProductVariants(product.id);
          return [product.id, variants] as const;
        })
      );
      const map: Record<number, AdminVariant[]> = {};
      for (const [productId, variants] of variantsEntries) {
        map[productId] = variants;
      }
      setVariantsByProduct(map);
    } catch {
      setError("No se pudo cargar el catalogo admin.");
    } finally {
      setLoading(false);
    }
  }

  async function loadTurns() {
    setTurnsError("");
    try {
      const rows = await listAdminTurns(turnsFilter === "all" ? undefined : turnsFilter);
      setTurns(rows);
    } catch {
      setTurnsError("No se pudieron cargar los turnos.");
    }
  }

  useEffect(() => {
    void loadAll();
  }, []);

  useEffect(() => {
    if (adminSection === "turnos") {
      void loadTurns();
    }
  }, [adminSection, turnsFilter]);

  async function onCreateProduct(event: FormEvent) {
    event.preventDefault();
    if (!hasCategories) {
      setError("Primero crea al menos una categoria en admin.");
      return;
    }
    setSavingNew(true);
    setError("");
    try {
      await createAdminProduct({
        name: newName.trim(),
        description: newDescription.trim() || null,
        img_url: newImgUrl.trim() || null,
        category: newCategory,
        active: true
      });
      setNewName("");
      setNewDescription("");
      setNewImgUrl("");
      await loadAll();
    } catch {
      setError("No se pudo crear el producto.");
    } finally {
      setSavingNew(false);
    }
  }

  async function onDeleteProduct(productId: number) {
    const confirmDelete = window.confirm("Eliminar producto? Esta accion es irreversible.");
    if (!confirmDelete) return;
    setError("");
    try {
      await deleteAdminProduct(productId);
      await loadAll();
    } catch {
      setError("No se pudo eliminar el producto.");
    }
  }

  function onStartEdit(product: AdminProduct) {
    setEditingProductId(product.id);
    setEditName(product.name || "");
    setEditDescription(product.description || "");
    setEditImgUrl(product.img_url || "");
    setEditCategory(product.category || categories[0]?.name || "");
    setEditActive(Boolean(product.active));
  }

  async function onSaveProductEdit() {
    if (!editingProductId) return;
    setError("");
    try {
      await patchAdminProduct(editingProductId, {
        name: editName.trim(),
        description: editDescription.trim() || null,
        img_url: editImgUrl.trim() || null,
        category: editCategory,
        active: editActive
      });
      setEditingProductId(null);
      await loadAll();
    } catch {
      setError("No se pudo actualizar el producto.");
    }
  }

  function onStartVariantEdit(variant: AdminVariant) {
    setEditingVariantId(variant.id);
    setEditVariantSku(variant.sku || "");
    setEditVariantSize(variant.size || "");
    setEditVariantColor(variant.color || "");
    setEditVariantImgUrl(variant.img_url || "");
    setEditVariantStock(String(variant.stock ?? 0));
    setEditVariantActive(Boolean(variant.active));
    setEnableVariantPriceEdit(false);
    setEditVariantPrice(String(variant.price ?? 0));
    setEditVariantOriginalPrice(variant.price ?? 0);
  }

  async function onSaveVariantEdit(variant: AdminVariant) {
    if (editingVariantId !== variant.id) return;
    setError("");
    try {
      const stockAsInt = Number.parseInt(editVariantStock, 10);
      if (Number.isNaN(stockAsInt) || stockAsInt < 0) {
        setError("Stock invalido.");
        return;
      }

      const payload: {
        sku: string;
        size: string | null;
        color: string | null;
        img_url: string | null;
        stock: number;
        active: boolean;
        price?: number;
      } = {
        sku: editVariantSku.trim(),
        size: editVariantSize.trim() || null,
        color: editVariantColor.trim() || null,
        img_url: editVariantImgUrl.trim() || null,
        stock: stockAsInt,
        active: editVariantActive
      };

      if (enableVariantPriceEdit) {
        const priceAsInt = Number.parseInt(editVariantPrice, 10);
        if (Number.isNaN(priceAsInt) || priceAsInt < 0) {
          setError("Precio invalido.");
          return;
        }
        if (priceAsInt !== editVariantOriginalPrice) {
          const confirmed = window.confirm(
            "Vas a cambiar el precio de la variante. Confirma para continuar."
          );
          if (!confirmed) return;
        }
        payload.price = priceAsInt;
      }

      await patchAdminVariant(variant.id, payload);
      setEditingVariantId(null);
      await loadAll();
    } catch {
      setError("No se pudo actualizar la variante.");
    }
  }

  const variantOptions = useMemo(() => {
    const rows: Array<{ value: string; label: string }> = [];
    for (const product of products) {
      const variants = variantsByProduct[product.id] ?? [];
      for (const variant of variants) {
        rows.push({
          value: String(variant.id),
          label: `${product.name} | ${variant.sku} (${variant.size || "-"} / ${variant.color || "-"})`
        });
      }
    }
    return rows.sort((a, b) => a.label.localeCompare(b.label));
  }, [products, variantsByProduct]);

  async function loadAdminOrder(orderId: number) {
    const [order, payments] = await Promise.all([getAdminOrder(orderId), listAdminOrderPayments(orderId)]);
    setSelectedOrder(order);
    setOrderPayments(payments);
  }

  function onAddManualItem() {
    const parsedVariantId = Number.parseInt(manualVariantId, 10);
    const parsedQty = Number.parseInt(manualQuantity, 10);
    if (Number.isNaN(parsedVariantId) || parsedVariantId <= 0 || Number.isNaN(parsedQty) || parsedQty <= 0) {
      setOrderError("Item invalido para la orden manual.");
      return;
    }
    const option = variantOptions.find((row) => row.value === String(parsedVariantId));
    const label = option?.label || `Variante ${parsedVariantId}`;
    const existing = manualItems.find((row) => row.variant_id === parsedVariantId);
    if (existing) {
      setManualItems((prev) =>
        prev.map((row) => (row.variant_id === parsedVariantId ? { ...row, quantity: row.quantity + parsedQty } : row))
      );
    } else {
      setManualItems((prev) => [...prev, { variant_id: parsedVariantId, quantity: parsedQty, label }]);
    }
    setManualVariantId("");
    setManualQuantity("1");
    setOrderError("");
  }

  function removeManualItem(variantId: number) {
    setManualItems((prev) => prev.filter((row) => row.variant_id !== variantId));
  }

  async function onCreateManualOrder() {
    setOrderError("");
    setOrderSuccess("");
    if (manualItems.length === 0) {
      setOrderError("Agrega al menos un item.");
      return;
    }
    try {
      const response = await createManualSubmittedOrder({
        customer: {
          email: manualEmail.trim(),
          first_name: manualFirstName.trim(),
          last_name: manualLastName.trim(),
          phone: manualPhone.trim()
        },
        items: manualItems.map((row) => ({ variant_id: row.variant_id, quantity: row.quantity }))
      });
      const orderId = response.order.id;
      setOrderLookupId(String(orderId));
      await loadAdminOrder(orderId);
      setOrderSuccess(`Orden manual creada: #${orderId}`);
      setManualItems([]);
    } catch {
      setOrderError("No se pudo crear la orden manual.");
    }
  }

  async function onLookupOrder() {
    const parsedOrderId = Number.parseInt(orderLookupId, 10);
    if (Number.isNaN(parsedOrderId) || parsedOrderId <= 0) {
      setOrderError("Ingresa un Order ID valido.");
      return;
    }
    setOrderError("");
    setOrderSuccess("");
    try {
      await loadAdminOrder(parsedOrderId);
    } catch {
      setOrderError("No se pudo cargar esa orden.");
    }
  }

  async function onMarkOrderPaid() {
    if (!selectedOrder) return;
    const parsedAmount = Number.parseInt(manualPayAmount, 10);
    if (Number.isNaN(parsedAmount) || parsedAmount <= 0) {
      setOrderError("Monto invalido para confirmar pago manual.");
      return;
    }
    if (!manualPayRef.trim()) {
      setOrderError("Payment ref requerida.");
      return;
    }
    setOrderError("");
    setOrderSuccess("");
    try {
      const updated = await adminMarkOrderPaid(selectedOrder.id, manualPayRef.trim(), parsedAmount);
      setSelectedOrder(updated);
      await loadAdminOrder(selectedOrder.id);
      setOrderSuccess(`Orden #${selectedOrder.id} marcada como pagada.`);
    } catch {
      setOrderError("No se pudo marcar la orden como pagada.");
    }
  }

  async function onUpdateTurnStatus(turnId: number, status: "confirmed" | "cancelled") {
    setTurnsError("");
    try {
      await updateAdminTurnStatus(turnId, status);
      await loadTurns();
    } catch {
      setTurnsError("No se pudo actualizar el estado del turno.");
    }
  }

  const productsSorted = useMemo(
    () => [...products].sort((a, b) => String(a.name).localeCompare(String(b.name))),
    [products]
  );

  return (
    <section>
      <h1 className="page-title">Panel Admin</h1>
      <p className="page-subtitle">Elegi que queres gestionar: catalogo, turnos, ordenes o pagos.</p>
      <div className="admin-section-tabs">
        <button className={`btn btn-small ${adminSection === "catalogo" ? "" : "btn-ghost"}`} type="button" onClick={() => setAdminSection("catalogo")}>
          Catalogo
        </button>
        <button className={`btn btn-small ${adminSection === "turnos" ? "" : "btn-ghost"}`} type="button" onClick={() => setAdminSection("turnos")}>
          Turnos
        </button>
        <button className={`btn btn-small ${adminSection === "ordenes" ? "" : "btn-ghost"}`} type="button" onClick={() => setAdminSection("ordenes")}>
          Ordenes
        </button>
        <button className={`btn btn-small ${adminSection === "pagos" ? "" : "btn-ghost"}`} type="button" onClick={() => setAdminSection("pagos")}>
          Pagos
        </button>
      </div>
      {adminSection === "catalogo" && error && <p className="error">{error}</p>}

      {adminSection === "catalogo" && (
      <article className="card">
        <h2>Agregar producto</h2>
        <form className="admin-form-grid" onSubmit={onCreateProduct}>
          <label>
            Nombre
            <input
              className="input"
              value={newName}
              onChange={(event) => setNewName(event.target.value)}
              required
            />
          </label>
          <label>
            Categoria
            <select
              className="input"
              value={newCategory}
              onChange={(event) => setNewCategory(event.target.value)}
              required
            >
              {categories.map((category) => (
                <option key={category.id} value={category.name}>
                  {category.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            Descripcion
            <input
              className="input"
              value={newDescription}
              onChange={(event) => setNewDescription(event.target.value)}
            />
          </label>
          <label>
            Img URL
            <input className="input" value={newImgUrl} onChange={(event) => setNewImgUrl(event.target.value)} />
          </label>
          <div>
            <button className="btn" type="submit" disabled={savingNew}>
              {savingNew ? "Guardando..." : "Agregar producto"}
            </button>
          </div>
        </form>
      </article>
      )}

      {adminSection === "catalogo" && (loading ? (
        <p>Cargando catalogo...</p>
      ) : (
        <div className="admin-products-list">
          {productsSorted.map((product) => {
            const variants = variantsByProduct[product.id] ?? [];
            return (
              <article className="card" key={product.id}>
                <div className="admin-product-head">
                  <div>
                    <h2>{product.name}</h2>
                    <p className="muted">{product.description || "Sin descripcion"}</p>
                    <p className="muted">
                      Categoria: {product.category || "-"} | Precio base: {formatArs(product.min_var_price)}
                    </p>
                  </div>
                  <div className="admin-product-actions">
                    <button className="btn btn-small" type="button" onClick={() => onStartEdit(product)}>
                      Editar
                    </button>
                    <button className="btn btn-small btn-danger" type="button" onClick={() => onDeleteProduct(product.id)}>
                      Eliminar
                    </button>
                  </div>
                </div>

                {editingProductId === product.id && (
                  <div className="admin-edit-box">
                    <h3>Editar producto</h3>
                    <div className="admin-form-grid">
                      <label>
                        Nombre
                        <input className="input" value={editName} onChange={(e) => setEditName(e.target.value)} />
                      </label>
                      <label>
                        Categoria
                        <select className="input" value={editCategory} onChange={(e) => setEditCategory(e.target.value)}>
                          {categories.map((category) => (
                            <option key={category.id} value={category.name}>
                              {category.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label>
                        Descripcion
                        <input className="input" value={editDescription} onChange={(e) => setEditDescription(e.target.value)} />
                      </label>
                      <label>
                        Img URL
                        <input className="input" value={editImgUrl} onChange={(e) => setEditImgUrl(e.target.value)} />
                      </label>
                      <label>
                        Activo
                        <select className="input" value={editActive ? "1" : "0"} onChange={(e) => setEditActive(e.target.value === "1")}>
                          <option value="1">Si</option>
                          <option value="0">No</option>
                        </select>
                      </label>
                    </div>
                    <div className="admin-product-actions">
                      <button className="btn btn-small" type="button" onClick={onSaveProductEdit}>
                        Guardar cambios
                      </button>
                      <button className="btn btn-small btn-ghost" type="button" onClick={() => setEditingProductId(null)}>
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}

                {variants.length === 0 ? (
                  <p className="muted">Sin variantes.</p>
                ) : (
                  <div className="admin-variants-grid">
                    {variants.map((variant) => (
                      <div className="admin-variant-row" key={variant.id}>
                        <p>
                          <strong>{variant.sku}</strong> ({variant.size || "-"} / {variant.color || "-"})
                        </p>
                        <p className="muted">Precio: {formatArs(variant.price)}</p>
                        <p className="muted">Stock: {variant.stock}</p>
                        <div className="admin-product-actions">
                          <button className="btn btn-small btn-ghost" type="button" onClick={() => onStartVariantEdit(variant)}>
                            Editar variante
                          </button>
                        </div>

                        {editingVariantId === variant.id && (
                          <div className="admin-edit-box admin-variant-edit-box">
                            <h3>Editar variante</h3>
                            <div className="admin-form-grid">
                              <label>
                                SKU
                                <input className="input" value={editVariantSku} onChange={(e) => setEditVariantSku(e.target.value)} />
                              </label>
                              <label>
                                Talle
                                <input className="input" value={editVariantSize} onChange={(e) => setEditVariantSize(e.target.value)} />
                              </label>
                              <label>
                                Color
                                <input className="input" value={editVariantColor} onChange={(e) => setEditVariantColor(e.target.value)} />
                              </label>
                              <label>
                                Img URL
                                <input className="input" value={editVariantImgUrl} onChange={(e) => setEditVariantImgUrl(e.target.value)} />
                              </label>
                              <label>
                                Stock
                                <input className="input" type="number" min={0} value={editVariantStock} onChange={(e) => setEditVariantStock(e.target.value)} />
                              </label>
                              <label>
                                Activa
                                <select className="input" value={editVariantActive ? "1" : "0"} onChange={(e) => setEditVariantActive(e.target.value === "1")}>
                                  <option value="1">Si</option>
                                  <option value="0">No</option>
                                </select>
                              </label>
                            </div>

                            <div className="admin-variant-price-guard">
                              <label>
                                <input
                                  type="checkbox"
                                  checked={enableVariantPriceEdit}
                                  onChange={(e) => setEnableVariantPriceEdit(e.target.checked)}
                                />
                                Habilitar cambio de precio (protegido)
                              </label>
                              {enableVariantPriceEdit && (
                                <label>
                                  Precio (centavos ARS)
                                  <input
                                    className="input"
                                    type="number"
                                    min={0}
                                    value={editVariantPrice}
                                    onChange={(e) => setEditVariantPrice(e.target.value)}
                                  />
                                </label>
                              )}
                            </div>

                            <div className="admin-product-actions">
                              <button className="btn btn-small" type="button" onClick={() => void onSaveVariantEdit(variant)}>
                                Guardar variante
                              </button>
                              <button className="btn btn-small btn-ghost" type="button" onClick={() => setEditingVariantId(null)}>
                                Cancelar
                              </button>
                            </div>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      ))}

      {adminSection === "turnos" && (
      <article className="card admin-orders-section">
        <h2>Admin Turnos</h2>
        <div className="admin-inline-actions">
          <select className="input" value={turnsFilter} onChange={(e) => setTurnsFilter(e.target.value as "all" | "pending" | "confirmed" | "cancelled")}>
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
      )}

      {(adminSection === "ordenes" || adminSection === "pagos") && (
      <article className="card admin-orders-section">
        <h2>{adminSection === "ordenes" ? "Admin Ordenes" : "Admin Pagos"}</h2>
        <p className="muted">
          {adminSection === "ordenes"
            ? "Crear orden manual y consultar orden por ID."
            : "Gestionar pagos de una orden y confirmar pago manual."}
        </p>
        {orderError && <p className="error">{orderError}</p>}
        {orderSuccess && <p className="success">{orderSuccess}</p>}

        {adminSection === "ordenes" && (
        <>
        <h3>Crear orden manual (submitted)</h3>
        <form
          className="admin-form-grid"
          onSubmit={(event) => {
            event.preventDefault();
            void onCreateManualOrder();
          }}
        >
          <label>
            Email cliente
            <input className="input" type="email" value={manualEmail} onChange={(e) => setManualEmail(e.target.value)} required />
          </label>
          <label>
            Nombre
            <input className="input" value={manualFirstName} onChange={(e) => setManualFirstName(e.target.value)} required />
          </label>
          <label>
            Apellido
            <input className="input" value={manualLastName} onChange={(e) => setManualLastName(e.target.value)} required />
          </label>
          <label>
            Telefono
            <input className="input" value={manualPhone} onChange={(e) => setManualPhone(e.target.value)} required />
          </label>
        </form>
        <div className="admin-form-grid">
          <label>
            Variante
            <select className="input" value={manualVariantId} onChange={(e) => setManualVariantId(e.target.value)}>
              <option value="">Seleccionar variante</option>
              {variantOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Cantidad
            <input className="input" type="number" min={1} value={manualQuantity} onChange={(e) => setManualQuantity(e.target.value)} />
          </label>
          <div className="admin-inline-actions">
            <button className="btn btn-small btn-ghost" type="button" onClick={onAddManualItem}>
              Agregar item
            </button>
          </div>
        </div>
        {manualItems.length > 0 && (
          <div className="admin-variants-grid">
            {manualItems.map((item) => (
              <div className="admin-variant-row" key={item.variant_id}>
                <p>{item.label}</p>
                <p className="muted">Cantidad: {item.quantity}</p>
                <div className="admin-product-actions">
                  <button className="btn btn-small btn-danger" type="button" onClick={() => removeManualItem(item.variant_id)}>
                    Quitar
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        <div className="admin-inline-actions">
          <button className="btn" type="button" onClick={() => setManualItems([])}>
            Limpiar items
          </button>
          <button className="btn" type="button" onClick={() => void onCreateManualOrder()}>
            Crear orden manual
          </button>
        </div>
        </>
        )}

        <h3>{adminSection === "ordenes" ? "Consultar orden" : "Consultar orden para pagos"}</h3>
        <div className="admin-form-grid">
          <label>
            Order ID
            <input className="input" value={orderLookupId} onChange={(e) => setOrderLookupId(e.target.value)} />
          </label>
          <div className="admin-inline-actions">
            <button className="btn btn-small" type="button" onClick={() => void onLookupOrder()}>
              Buscar orden
            </button>
          </div>
        </div>

        {selectedOrder && (
          <div className="admin-edit-box">
            <p>
              <strong>Orden #{selectedOrder.id}</strong> | Estado: {selectedOrder.status} | Total: {formatArs(selectedOrder.total_amount)}
            </p>
            <div className="admin-variants-grid">
              {selectedOrder.items.map((item) => (
                <div className="admin-variant-row" key={item.id}>
                  <p>
                    {item.product_name || "Producto"} - {item.variant_label}
                  </p>
                  <p className="muted">Qty: {item.quantity}</p>
                  <p className="muted">Subtotal linea: {formatArs(item.line_total)}</p>
                </div>
              ))}
            </div>

            {adminSection === "pagos" && (
              <>
                <div className="admin-form-grid">
                  <label>
                    Ref pago manual
                    <input className="input" value={manualPayRef} onChange={(e) => setManualPayRef(e.target.value)} />
                  </label>
                  <label>
                    Monto (centavos ARS)
                    <input className="input" type="number" min={1} value={manualPayAmount} onChange={(e) => setManualPayAmount(e.target.value)} />
                  </label>
                  <div className="admin-inline-actions">
                    <button className="btn btn-small" type="button" onClick={() => void onMarkOrderPaid()}>
                      Marcar como pagada
                    </button>
                  </div>
                </div>

                <h4>Pagos</h4>
                {orderPayments.length === 0 ? (
                  <p className="muted">Sin pagos para esta orden.</p>
                ) : (
                  <div className="admin-variants-grid">
                    {orderPayments.map((payment) => (
                      <div className="admin-variant-row" key={payment.id}>
                        <p>
                          #{payment.id} {payment.method}
                        </p>
                        <p className="muted">Estado: {payment.status}</p>
                        <p className="muted">Monto: {formatArs(payment.amount)}</p>
                        <p className="muted">Ref: {payment.external_ref || "-"}</p>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </div>
        )}
      </article>
      )}
    </section>
  );
}
