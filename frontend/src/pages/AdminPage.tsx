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
  listAdminOrders,
  listAdminOrderPayments,
  listAdminPayments,
  type AdminOrder,
  type AdminPayment
} from "../services/admin-orders-api";
import {
  createAdminDiscount,
  deleteAdminDiscount,
  listAdminDiscounts,
  patchAdminDiscount,
  type AdminDiscount
} from "../services/admin-discounts-api";
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
  const [adminSection, setAdminSection] = useState<"catalogo" | "descuentos" | "turnos" | "ordenes" | "pagos">("catalogo");
  const [products, setProducts] = useState<AdminProduct[]>([]);
  const [categories, setCategories] = useState<AdminCategory[]>([]);
  const [variantsByProduct, setVariantsByProduct] = useState<Record<number, AdminVariant[]>>({});
  const [expandedProducts, setExpandedProducts] = useState<Record<number, boolean>>({});
  const [openProductMenuId, setOpenProductMenuId] = useState<number | null>(null);
  const [showCreateProductForm, setShowCreateProductForm] = useState(false);
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
  const [selectedOrder, setSelectedOrder] = useState<AdminOrder | null>(null);
  const [orderPayments, setOrderPayments] = useState<AdminPayment[]>([]);
  const [ordersList, setOrdersList] = useState<AdminOrder[]>([]);
  const [ordersListLoading, setOrdersListLoading] = useState(false);
  const [ordersFilter, setOrdersFilter] = useState<"all" | "submitted" | "paid" | "cancelled">("all");
  const [ordersShowAll, setOrdersShowAll] = useState(false);
  const [ordersSortBy, setOrdersSortBy] = useState<"created_at" | "id">("created_at");
  const [ordersSortDir, setOrdersSortDir] = useState<"desc" | "asc">("desc");
  const [paymentsList, setPaymentsList] = useState<AdminPayment[]>([]);
  const [paymentsListLoading, setPaymentsListLoading] = useState(false);
  const [paymentsFilter, setPaymentsFilter] = useState<"all" | "pending" | "paid" | "cancelled" | "expired">("all");
  const [paymentsShowAll, setPaymentsShowAll] = useState(false);
  const [paymentsSortBy, setPaymentsSortBy] = useState<"created_at" | "id">("created_at");
  const [paymentsSortDir, setPaymentsSortDir] = useState<"desc" | "asc">("desc");
  const [showCreateManualOrderForm, setShowCreateManualOrderForm] = useState(false);
  const [showManualPaymentForm, setShowManualPaymentForm] = useState(false);
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
  const [discounts, setDiscounts] = useState<AdminDiscount[]>([]);
  const [discountsLoading, setDiscountsLoading] = useState(false);
  const [discountsError, setDiscountsError] = useState("");
  const [showCreateDiscountForm, setShowCreateDiscountForm] = useState(false);
  const [newDiscountName, setNewDiscountName] = useState("");
  const [newDiscountType, setNewDiscountType] = useState<"percent" | "fixed">("percent");
  const [newDiscountValue, setNewDiscountValue] = useState("10");
  const [newDiscountTarget, setNewDiscountTarget] = useState<"all" | "category" | "products">("all");
  const [newDiscountCategoryId, setNewDiscountCategoryId] = useState("");
  const [showDiscountProductPicker, setShowDiscountProductPicker] = useState(false);
  const [discountPickerExpandedProducts, setDiscountPickerExpandedProducts] = useState<Record<number, boolean>>({});
  const [selectedDiscountProductIds, setSelectedDiscountProductIds] = useState<Record<number, boolean>>({});
  const [selectedDiscountVariantIds, setSelectedDiscountVariantIds] = useState<Record<number, boolean>>({});
  const [newDiscountActive, setNewDiscountActive] = useState(true);

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

  async function loadDiscounts() {
    setDiscountsLoading(true);
    setDiscountsError("");
    try {
      const rows = await listAdminDiscounts();
      setDiscounts(rows);
    } catch {
      setDiscountsError("No se pudieron cargar los descuentos.");
    } finally {
      setDiscountsLoading(false);
    }
  }

  useEffect(() => {
    void loadAll();
  }, []);

  useEffect(() => {
    if (adminSection === "turnos") {
      void loadTurns();
    }
    if (adminSection === "descuentos") {
      void loadDiscounts();
    }
  }, [adminSection, turnsFilter]);

  useEffect(() => {
    async function loadOrdersPanelList() {
      if (adminSection !== "ordenes") return;
      setOrdersListLoading(true);
      setOrderError("");
      try {
        const rows = await listAdminOrders({
          status: ordersFilter === "all" ? undefined : ordersFilter,
          limit: ordersShowAll ? 500 : 10,
          sort_by: ordersSortBy,
          sort_dir: ordersSortDir
        });
        setOrdersList(rows);
      } catch {
        setOrderError("No se pudieron cargar las ordenes.");
      } finally {
        setOrdersListLoading(false);
      }
    }
    void loadOrdersPanelList();
  }, [adminSection, ordersFilter, ordersShowAll, ordersSortBy, ordersSortDir]);

  useEffect(() => {
    async function loadPaymentsPanelList() {
      if (adminSection !== "pagos") return;
      setPaymentsListLoading(true);
      setOrderError("");
      try {
        const rows = await listAdminPayments({
          status: paymentsFilter === "all" ? undefined : paymentsFilter,
          limit: paymentsShowAll ? 500 : 10,
          sort_by: paymentsSortBy,
          sort_dir: paymentsSortDir
        });
        setPaymentsList(rows);
      } catch {
        setOrderError("No se pudieron cargar los pagos.");
      } finally {
        setPaymentsListLoading(false);
      }
    }
    void loadPaymentsPanelList();
  }, [adminSection, paymentsFilter, paymentsShowAll, paymentsSortBy, paymentsSortDir]);

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
      setOpenProductMenuId(null);
      await loadAll();
    } catch {
      setError("No se pudo eliminar el producto.");
    }
  }

  function onStartEdit(product: AdminProduct) {
    setExpandedProducts((prev) => ({ ...prev, [product.id]: true }));
    setOpenProductMenuId(null);
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
      setOpenProductMenuId(null);
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

  function toggleProductExpanded(productId: number) {
    setExpandedProducts((prev) => ({ ...prev, [productId]: !prev[productId] }));
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
      await loadAdminOrder(orderId);
      setOrderSuccess(`Orden manual creada: #${orderId}`);
      setManualItems([]);
      setShowCreateManualOrderForm(false);
    } catch {
      setOrderError("No se pudo crear la orden manual.");
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

  function toggleDiscountPickerProductExpanded(productId: number) {
    setDiscountPickerExpandedProducts((prev) => ({ ...prev, [productId]: !prev[productId] }));
  }

  function toggleDiscountProductSelection(productId: number, checked: boolean) {
    const variants = variantsByProduct[productId] ?? [];
    setSelectedDiscountProductIds((prev) => ({ ...prev, [productId]: checked }));
    setSelectedDiscountVariantIds((prev) => {
      const next = { ...prev };
      for (const variant of variants) {
        next[variant.id] = checked;
      }
      return next;
    });
  }

  function toggleDiscountVariantSelection(productId: number, variantId: number, checked: boolean) {
    const variants = variantsByProduct[productId] ?? [];
    setSelectedDiscountVariantIds((prev) => {
      const next = { ...prev, [variantId]: checked };
      setSelectedDiscountProductIds((prevProducts) => ({
        ...prevProducts,
        [productId]: variants.length > 0 && variants.every((variant) => !!next[variant.id])
      }));
      return next;
    });
  }

  async function onCreateDiscount() {
    setDiscountsError("");
    try {
      const parsedValue = Number.parseInt(newDiscountValue, 10);
      if (Number.isNaN(parsedValue) || parsedValue <= 0) {
        setDiscountsError("Valor de descuento invalido.");
        return;
      }
      const variantToProductId = new Map<number, number>();
      for (const productVariants of Object.values(variantsByProduct)) {
        for (const variant of productVariants) {
          variantToProductId.set(variant.id, variant.product_id);
        }
      }
      const selectedProductIdsFromVariants = Array.from(
        new Set(
          Object.entries(selectedDiscountVariantIds)
            .filter(([, selected]) => selected)
            .map(([variantId]) => variantToProductId.get(Number.parseInt(variantId, 10)))
            .filter((productId): productId is number => typeof productId === "number" && productId > 0)
        )
      );
      const selectedDirectProductIds = Object.entries(selectedDiscountProductIds)
        .filter(([, selected]) => selected)
        .map(([productId]) => Number.parseInt(productId, 10))
        .filter((productId) => Number.isFinite(productId) && productId > 0);
      const mergedProductIds = Array.from(new Set([...selectedProductIdsFromVariants, ...selectedDirectProductIds]));

      if (newDiscountTarget === "category") {
        const parsedCategoryId = Number.parseInt(newDiscountCategoryId, 10);
        if (Number.isNaN(parsedCategoryId) || parsedCategoryId <= 0) {
          setDiscountsError("Elegi una categoria valida.");
          return;
        }
      }
      if (newDiscountTarget === "products" && mergedProductIds.length === 0) {
        setDiscountsError("Selecciona al menos un producto o variante.");
        return;
      }

      const scope: "all" | "category" | "product" | "product_list" =
        newDiscountTarget === "all"
          ? "all"
          : newDiscountTarget === "category"
            ? "category"
            : mergedProductIds.length === 1
              ? "product"
              : "product_list";

      await createAdminDiscount({
        name: newDiscountName.trim(),
        type: newDiscountType,
        value: parsedValue,
        scope,
        category_id: scope === "category" ? Number.parseInt(newDiscountCategoryId, 10) : null,
        product_id: scope === "product" ? mergedProductIds[0] : null,
        product_ids: scope === "product_list" ? mergedProductIds : [],
        is_active: newDiscountActive
      });
      setNewDiscountName("");
      setNewDiscountValue("10");
      setNewDiscountTarget("all");
      setNewDiscountCategoryId("");
      setSelectedDiscountProductIds({});
      setSelectedDiscountVariantIds({});
      setShowDiscountProductPicker(false);
      setNewDiscountActive(true);
      setShowCreateDiscountForm(false);
      await loadDiscounts();
    } catch {
      setDiscountsError("No se pudo crear el descuento.");
    }
  }

  async function onToggleDiscountActive(discount: AdminDiscount) {
    setDiscountsError("");
    try {
      await patchAdminDiscount(discount.id, { is_active: !discount.is_active });
      await loadDiscounts();
    } catch {
      setDiscountsError("No se pudo actualizar el descuento.");
    }
  }

  async function onDeleteDiscount(discountId: number) {
    const confirmed = window.confirm("Eliminar descuento?");
    if (!confirmed) return;
    setDiscountsError("");
    try {
      await deleteAdminDiscount(discountId);
      await loadDiscounts();
    } catch {
      setDiscountsError("No se pudo eliminar el descuento.");
    }
  }

  const productsSorted = useMemo(
    () => [...products].sort((a, b) => String(a.name).localeCompare(String(b.name))),
    [products]
  );
  const selectedDiscountVariantCount = useMemo(
    () => Object.values(selectedDiscountVariantIds).filter(Boolean).length,
    [selectedDiscountVariantIds]
  );
  const selectedDiscountProductCount = useMemo(() => {
    const direct = Object.entries(selectedDiscountProductIds)
      .filter(([, selected]) => selected)
      .map(([productId]) => Number.parseInt(productId, 10))
      .filter((productId) => Number.isFinite(productId) && productId > 0);
    const variantProducts = Object.entries(selectedDiscountVariantIds)
      .filter(([, selected]) => selected)
      .map(([variantId]) => {
        const numericVariantId = Number.parseInt(variantId, 10);
        for (const productVariants of Object.values(variantsByProduct)) {
          const match = productVariants.find((variant) => variant.id === numericVariantId);
          if (match) return match.product_id;
        }
        return null;
      })
      .filter((productId): productId is number => typeof productId === "number" && productId > 0);
    return new Set([...direct, ...variantProducts]).size;
  }, [selectedDiscountProductIds, selectedDiscountVariantIds, variantsByProduct]);

  return (
    <section>
      <h1 className="page-title">Panel Admin</h1>
      <p className="page-subtitle">Elegi que queres gestionar: catalogo, turnos, ordenes o pagos.</p>
      <div className="admin-section-tabs">
        <button className={`btn btn-small ${adminSection === "catalogo" ? "" : "btn-ghost"}`} type="button" onClick={() => setAdminSection("catalogo")}>
          Catalogo
        </button>
        <button className={`btn btn-small ${adminSection === "descuentos" ? "" : "btn-ghost"}`} type="button" onClick={() => setAdminSection("descuentos")}>
          Descuentos
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

      {adminSection === "descuentos" && (
        <article className="card admin-orders-section">
          <h2>Admin Descuentos</h2>
          <div className="admin-inline-actions">
            <button className="btn btn-small btn-ghost" type="button" onClick={() => setShowCreateDiscountForm((v) => !v)}>
              {showCreateDiscountForm ? "Ocultar crear descuento" : "Crear descuento"}
            </button>
            <button className="btn btn-small" type="button" onClick={() => void loadDiscounts()}>
              Refrescar
            </button>
          </div>
          {discountsError && <p className="error">{discountsError}</p>}

          {showCreateDiscountForm && (
            <>
              <h3>Nuevo descuento</h3>
              <div className="admin-form-grid">
                <label>
                  Nombre
                  <input className="input" value={newDiscountName} onChange={(e) => setNewDiscountName(e.target.value)} />
                </label>
                <label>
                  Tipo
                  <select className="input" value={newDiscountType} onChange={(e) => setNewDiscountType(e.target.value as "percent" | "fixed")}>
                    <option value="percent">Percent</option>
                    <option value="fixed">Fixed</option>
                  </select>
                </label>
                <label>
                  Valor
                  <input className="input" type="number" min={1} value={newDiscountValue} onChange={(e) => setNewDiscountValue(e.target.value)} />
                </label>
                <label>
                  Alcance inicial
                  <select className="input" value={newDiscountTarget} onChange={(e) => setNewDiscountTarget(e.target.value as "all" | "category" | "products")}>
                    <option value="all">Todo el catalogo</option>
                    <option value="category">Categoria</option>
                    <option value="products">Producto(s)</option>
                  </select>
                </label>
                {newDiscountTarget === "category" && (
                  <label>
                    Categoria
                    <select className="input" value={newDiscountCategoryId} onChange={(e) => setNewDiscountCategoryId(e.target.value)}>
                      <option value="">Seleccionar categoria...</option>
                      {categories.map((category) => (
                        <option key={category.id} value={String(category.id)}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
                <label>
                  Activo
                  <select className="input" value={newDiscountActive ? "1" : "0"} onChange={(e) => setNewDiscountActive(e.target.value === "1")}>
                    <option value="1">Si</option>
                    <option value="0">No</option>
                  </select>
                </label>
              </div>
              {newDiscountTarget === "products" && (
                <div className="admin-discount-picker-wrap">
                  <div className="admin-inline-actions">
                    <button
                      className="btn btn-small btn-ghost"
                      type="button"
                      onClick={() => setShowDiscountProductPicker((prev) => !prev)}
                    >
                      {showDiscountProductPicker ? "Ocultar selector" : "Seleccionar productos"}
                    </button>
                  </div>
                  <p className="muted">
                    Seleccionados: {selectedDiscountProductCount} productos,
                    {" "}
                    {selectedDiscountVariantCount} variantes.
                  </p>
                  {showDiscountProductPicker && (
                    <div className="admin-discount-picker-list">
                      {productsSorted.map((product) => {
                        const variants = variantsByProduct[product.id] ?? [];
                        return (
                          <article className="card" key={`discount-picker-${product.id}`}>
                            <div className="admin-product-head">
                              <button
                                className="admin-expand-btn"
                                type="button"
                                onClick={() => toggleDiscountPickerProductExpanded(product.id)}
                                aria-label={discountPickerExpandedProducts[product.id] ? "Contraer producto" : "Expandir producto"}
                              >
                                {discountPickerExpandedProducts[product.id] ? "▾" : "▸"}
                              </button>
                              <label className="admin-discount-product-check">
                                <input
                                  type="checkbox"
                                  checked={!!selectedDiscountProductIds[product.id]}
                                  onChange={(event) => toggleDiscountProductSelection(product.id, event.target.checked)}
                                />
                                <span>
                                  <strong>{product.name}</strong>
                                  <span className="muted"> #{product.id}</span>
                                </span>
                              </label>
                            </div>
                            {discountPickerExpandedProducts[product.id] && (
                              <div className="admin-variants-grid">
                                {variants.length === 0 ? (
                                  <p className="muted">Sin variantes.</p>
                                ) : (
                                  variants.map((variant) => (
                                    <label className="admin-discount-variant-check" key={`discount-picker-variant-${variant.id}`}>
                                      <input
                                        type="checkbox"
                                        checked={!!selectedDiscountVariantIds[variant.id]}
                                        onChange={(event) => toggleDiscountVariantSelection(product.id, variant.id, event.target.checked)}
                                      />
                                      <span>
                                        {variant.sku} | Talle: {variant.size || "-"} | Color: {variant.color || "-"} | {formatArs(variant.price)}
                                      </span>
                                    </label>
                                  ))
                                )}
                              </div>
                            )}
                          </article>
                        );
                      })}
                    </div>
                  )}
                </div>
              )}
              <div className="admin-inline-actions">
                <button className="btn btn-small" type="button" onClick={() => void onCreateDiscount()}>
                  Guardar descuento
                </button>
              </div>
            </>
          )}

          <h3>Listado</h3>
          {discountsLoading ? (
            <p>Cargando descuentos...</p>
          ) : discounts.length === 0 ? (
            <p className="muted">No hay descuentos configurados.</p>
          ) : (
            <div className="admin-scroll-list">
              {discounts.map((discount) => (
                <div className="admin-variant-row" key={discount.id}>
                  <p><strong>#{discount.id}</strong> {discount.name}</p>
                  <p className="muted">{discount.type} {discount.value} | {discount.scope}</p>
                  <p className="muted">{discount.is_active ? "Activo" : "Inactivo"}</p>
                  <div className="admin-product-actions">
                    <button className="btn btn-small btn-ghost" type="button" onClick={() => void onToggleDiscountActive(discount)}>
                      {discount.is_active ? "Desactivar" : "Activar"}
                    </button>
                    <button className="btn btn-small btn-danger" type="button" onClick={() => void onDeleteDiscount(discount.id)}>
                      Eliminar
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </article>
      )}

      {adminSection === "catalogo" && (
      <article className="card">
        <div className="admin-inline-actions">
          <button className="btn btn-small btn-ghost" type="button" onClick={() => setShowCreateProductForm((v) => !v)}>
            {showCreateProductForm ? "Ocultar crear producto" : "Agregar producto"}
          </button>
        </div>
        {showCreateProductForm && (
          <>
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
          </>
        )}
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
                  <button
                    className="admin-expand-btn"
                    type="button"
                    onClick={() => toggleProductExpanded(product.id)}
                    aria-label={expandedProducts[product.id] ? "Contraer producto" : "Expandir producto"}
                  >
                    {expandedProducts[product.id] ? "▾" : "▸"}
                  </button>
                  <div className="admin-product-summary">
                    <h2>{product.name}</h2>
                    <p className="muted">{product.description || "Sin descripcion"}</p>
                    <p className="muted">
                      Categoria: {product.category || "-"} | Precio base: {formatArs(product.min_var_price)}
                    </p>
                  </div>
                  <div className="admin-product-menu-wrap">
                    <button
                      className="btn btn-small btn-ghost"
                      type="button"
                      onClick={() => setOpenProductMenuId((prev) => (prev === product.id ? null : product.id))}
                      aria-label="Opciones de producto"
                    >
                      ⋯
                    </button>
                    {openProductMenuId === product.id && (
                      <div className="admin-product-menu">
                        <button className="btn btn-small btn-ghost" type="button" onClick={() => onStartEdit(product)}>
                          Editar
                        </button>
                        <button className="btn btn-small btn-danger" type="button" onClick={() => void onDeleteProduct(product.id)}>
                          Eliminar
                        </button>
                      </div>
                    )}
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

                {expandedProducts[product.id] && (
                  variants.length === 0 ? (
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
                  )
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
            ? "Ultimas ordenes, filtros por estado y orden por fecha o id."
            : "Ultimos pagos, filtros por estado y orden por fecha o id."}
        </p>
        {orderError && <p className="error">{orderError}</p>}
        {orderSuccess && <p className="success">{orderSuccess}</p>}

        {adminSection === "ordenes" && (
        <>
        <div className="admin-inline-actions">
          <button className="btn btn-small btn-ghost" type="button" onClick={() => setShowCreateManualOrderForm((v) => !v)}>
            {showCreateManualOrderForm ? "Ocultar crear orden" : "Crear orden manual"}
          </button>
          <select className="input" value={ordersFilter} onChange={(e) => setOrdersFilter(e.target.value as "all" | "submitted" | "paid" | "cancelled")}>
            <option value="all">Todas</option>
            <option value="submitted">Submitted</option>
            <option value="paid">Paid</option>
            <option value="cancelled">Cancelled</option>
          </select>
          <select className="input" value={ordersSortBy} onChange={(e) => setOrdersSortBy(e.target.value as "created_at" | "id")}>
            <option value="created_at">Ordenar por fecha</option>
            <option value="id">Ordenar por ID</option>
          </select>
          <select className="input" value={ordersSortDir} onChange={(e) => setOrdersSortDir(e.target.value as "desc" | "asc")}>
            <option value="desc">Desc</option>
            <option value="asc">Asc</option>
          </select>
          <button className="btn btn-small" type="button" onClick={() => setOrdersShowAll((v) => !v)}>
            {ordersShowAll ? "Mostrar ultimas 10" : "Mostrar todas"}
          </button>
        </div>

        {showCreateManualOrderForm && (
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

        <h3>Listado de ordenes</h3>
        {ordersListLoading ? (
          <p>Cargando ordenes...</p>
        ) : ordersList.length === 0 ? (
          <p className="muted">Sin ordenes para mostrar.</p>
        ) : (
          <div className="admin-scroll-list">
            {ordersList.map((order) => (
              <div className="admin-variant-row" key={order.id}>
                <p><strong>#{order.id}</strong></p>
                <p className="muted">Estado: {order.status}</p>
                <p className="muted">Total: {formatArs(order.total_amount)}</p>
                <div className="admin-product-actions">
                  <button className="btn btn-small" type="button" onClick={() => void loadAdminOrder(order.id)}>
                    Ver detalle
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
        </>
        )}
        {adminSection === "pagos" && (
          <>
            <div className="admin-inline-actions">
              <select className="input" value={paymentsFilter} onChange={(e) => setPaymentsFilter(e.target.value as "all" | "pending" | "paid" | "cancelled" | "expired")}>
                <option value="all">Todos</option>
                <option value="pending">Pending</option>
                <option value="paid">Paid</option>
                <option value="cancelled">Cancelled</option>
                <option value="expired">Expired</option>
              </select>
              <select className="input" value={paymentsSortBy} onChange={(e) => setPaymentsSortBy(e.target.value as "created_at" | "id")}>
                <option value="created_at">Ordenar por fecha</option>
                <option value="id">Ordenar por ID</option>
              </select>
              <select className="input" value={paymentsSortDir} onChange={(e) => setPaymentsSortDir(e.target.value as "desc" | "asc")}>
                <option value="desc">Desc</option>
                <option value="asc">Asc</option>
              </select>
              <button className="btn btn-small" type="button" onClick={() => setPaymentsShowAll((v) => !v)}>
                {paymentsShowAll ? "Mostrar ultimos 10" : "Mostrar todos"}
              </button>
              <button className="btn btn-small btn-ghost" type="button" onClick={() => setShowManualPaymentForm((v) => !v)}>
                {showManualPaymentForm ? "Ocultar pago manual" : "Confirmar pago manual"}
              </button>
            </div>
            <h3>Listado de pagos</h3>
            {paymentsListLoading ? (
              <p>Cargando pagos...</p>
            ) : paymentsList.length === 0 ? (
              <p className="muted">Sin pagos para mostrar.</p>
            ) : (
              <div className="admin-scroll-list">
                {paymentsList.map((payment) => (
                  <div className="admin-variant-row" key={payment.id}>
                    <p><strong>#{payment.id}</strong> {payment.method}</p>
                    <p className="muted">Estado: {payment.status}</p>
                    <p className="muted">Monto: {formatArs(payment.amount)}</p>
                    <div className="admin-product-actions">
                      <button className="btn btn-small" type="button" onClick={() => void loadAdminOrder(payment.order_id)}>
                        Ver orden #{payment.order_id}
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

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
                {showManualPaymentForm && (
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
                )}

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
