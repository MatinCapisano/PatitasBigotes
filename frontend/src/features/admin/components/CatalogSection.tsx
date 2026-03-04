import type { FormEvent } from "react";
import type { AdminCategory, AdminProduct, AdminVariant } from "../services";

export function CatalogSection(props: {
  error: string;
  showCreateProductForm: boolean;
  setShowCreateProductForm: (value: boolean | ((prev: boolean) => boolean)) => void;
  onCreateProduct: (event: FormEvent) => Promise<void>;
  savingNew: boolean;
  newName: string;
  setNewName: (value: string) => void;
  newCategory: string;
  setNewCategory: (value: string) => void;
  categories: AdminCategory[];
  newDescription: string;
  setNewDescription: (value: string) => void;
  newImgUrl: string;
  setNewImgUrl: (value: string) => void;
  loading: boolean;
  productsSorted: AdminProduct[];
  variantsByProduct: Record<number, AdminVariant[]>;
  expandedProducts: Record<number, boolean>;
  toggleProductExpanded: (productId: number) => void;
  openProductMenuId: number | null;
  setOpenProductMenuId: (value: number | null | ((prev: number | null) => number | null)) => void;
  onStartEdit: (product: AdminProduct) => void;
  onDeleteProduct: (productId: number) => Promise<void>;
  editingProductId: number | null;
  editName: string;
  setEditName: (value: string) => void;
  editCategory: string;
  setEditCategory: (value: string) => void;
  editDescription: string;
  setEditDescription: (value: string) => void;
  editImgUrl: string;
  setEditImgUrl: (value: string) => void;
  editActive: boolean;
  setEditActive: (value: boolean) => void;
  onSaveProductEdit: () => Promise<void>;
  setEditingProductId: (value: number | null) => void;
  editingVariantId: number | null;
  onStartVariantEdit: (variant: AdminVariant) => void;
  editVariantSku: string;
  setEditVariantSku: (value: string) => void;
  editVariantSize: string;
  setEditVariantSize: (value: string) => void;
  editVariantColor: string;
  setEditVariantColor: (value: string) => void;
  editVariantImgUrl: string;
  setEditVariantImgUrl: (value: string) => void;
  editVariantStock: string;
  setEditVariantStock: (value: string) => void;
  editVariantActive: boolean;
  setEditVariantActive: (value: boolean) => void;
  enableVariantPriceEdit: boolean;
  setEnableVariantPriceEdit: (value: boolean) => void;
  editVariantPrice: string;
  setEditVariantPrice: (value: string) => void;
  onSaveVariantEdit: (variant: AdminVariant) => Promise<void>;
  setEditingVariantId: (value: number | null) => void;
  formatArs: (cents: number | null) => string;
}) {
  const {
    error,
    showCreateProductForm,
    setShowCreateProductForm,
    onCreateProduct,
    savingNew,
    newName,
    setNewName,
    newCategory,
    setNewCategory,
    categories,
    newDescription,
    setNewDescription,
    newImgUrl,
    setNewImgUrl,
    loading,
    productsSorted,
    variantsByProduct,
    expandedProducts,
    toggleProductExpanded,
    openProductMenuId,
    setOpenProductMenuId,
    onStartEdit,
    onDeleteProduct,
    editingProductId,
    editName,
    setEditName,
    editCategory,
    setEditCategory,
    editDescription,
    setEditDescription,
    editImgUrl,
    setEditImgUrl,
    editActive,
    setEditActive,
    onSaveProductEdit,
    setEditingProductId,
    editingVariantId,
    onStartVariantEdit,
    editVariantSku,
    setEditVariantSku,
    editVariantSize,
    setEditVariantSize,
    editVariantColor,
    setEditVariantColor,
    editVariantImgUrl,
    setEditVariantImgUrl,
    editVariantStock,
    setEditVariantStock,
    editVariantActive,
    setEditVariantActive,
    enableVariantPriceEdit,
    setEnableVariantPriceEdit,
    editVariantPrice,
    setEditVariantPrice,
    onSaveVariantEdit,
    setEditingVariantId,
    formatArs
  } = props;

  return (
    <>
      {error && <p className="error">{error}</p>}
      <article className="card">
        <div className="admin-inline-actions">
          <button className="btn btn-small btn-ghost" type="button" onClick={() => setShowCreateProductForm((v) => !v)}>
            {showCreateProductForm ? "Ocultar crear producto" : "Agregar producto"}
          </button>
        </div>
        {showCreateProductForm && (
          <>
            <h2>Agregar producto</h2>
            <form className="admin-form-grid" onSubmit={(event) => void onCreateProduct(event)}>
              <label>
                Nombre
                <input className="input" value={newName} onChange={(event) => setNewName(event.target.value)} required />
              </label>
              <label>
                Categoria
                <select className="input" value={newCategory} onChange={(event) => setNewCategory(event.target.value)} required>
                  {categories.map((category) => (
                    <option key={category.id} value={category.name}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Descripcion
                <input className="input" value={newDescription} onChange={(event) => setNewDescription(event.target.value)} />
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

      {loading ? (
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
                      <button className="btn btn-small" type="button" onClick={() => void onSaveProductEdit()}>
                        Guardar cambios
                      </button>
                      <button className="btn btn-small btn-ghost" type="button" onClick={() => setEditingProductId(null)}>
                        Cancelar
                      </button>
                    </div>
                  </div>
                )}

                {expandedProducts[product.id] &&
                  (variants.length === 0 ? (
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
                                  <input type="checkbox" checked={enableVariantPriceEdit} onChange={(e) => setEnableVariantPriceEdit(e.target.checked)} />
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
                  ))}
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}
