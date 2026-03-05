import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import {
  type AdminCategory,
  type AdminProduct,
  type AdminVariant,
  createAdminCategory,
  createAdminProduct,
  deleteAdminCategory,
  deleteAdminProduct,
  listAdminCategories,
  listAdminProducts,
  listProductVariants,
  patchAdminProduct,
  patchAdminVariant
} from "../../../services/admin-catalog-api";
import type { VariantOption } from "../types";

export function useAdminCatalog() {
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
  const [showCreateCategoryForm, setShowCreateCategoryForm] = useState(false);
  const [newCategoryName, setNewCategoryName] = useState("");
  const [creatingCategory, setCreatingCategory] = useState(false);
  const [catalogCategoryFilter, setCatalogCategoryFilter] = useState<string>("all");
  const [showAddStockModal, setShowAddStockModal] = useState(false);
  const [stockProductId, setStockProductId] = useState("");
  const [stockQuantity, setStockQuantity] = useState("1");
  const [addingStock, setAddingStock] = useState(false);
  const [stockSuccessMessage, setStockSuccessMessage] = useState("");

  const hasCategories = categories.length > 0;

  const loadAll = useCallback(async () => {
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
  }, [newCategory]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

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

  async function onCreateCategory(event: FormEvent) {
    event.preventDefault();
    const normalizedName = newCategoryName.trim();
    if (!normalizedName) {
      setError("Nombre de categoria requerido.");
      return;
    }
    setCreatingCategory(true);
    setError("");
    try {
      await createAdminCategory({ name: normalizedName });
      setNewCategoryName("");
      setShowCreateCategoryForm(false);
      await loadAll();
      setCatalogCategoryFilter(normalizedName);
      setNewCategory(normalizedName);
    } catch {
      setError("No se pudo crear la categoria.");
    } finally {
      setCreatingCategory(false);
    }
  }

  async function onDeleteCategory() {
    if (catalogCategoryFilter === "all") {
      setError("Selecciona una categoria para eliminar.");
      return;
    }
    const categoryName = catalogCategoryFilter;
    const category = categories.find((item) => item.name === categoryName);
    if (!category) {
      setError("Categoria no encontrada.");
      return;
    }
    const hasProducts = products.some((product) => String(product.category || "") === categoryName);
    if (hasProducts) {
      setError("No se puede eliminar una categoria con productos.");
      return;
    }
    const confirmDelete = window.confirm(`Eliminar categoria "${categoryName}"?`);
    if (!confirmDelete) return;
    setError("");
    try {
      await deleteAdminCategory(category.id);
      setCatalogCategoryFilter("all");
      await loadAll();
    } catch {
      setError("No se pudo eliminar la categoria.");
    }
  }

  function onOpenAddStockModal() {
    if (!stockProductId && products[0]?.id) {
      setStockProductId(String(products[0].id));
    }
    setStockQuantity("1");
    setStockSuccessMessage("");
    setShowAddStockModal(true);
    setError("");
  }

  async function onConfirmAddStock(selectedVariantIds: number[]) {
    const parsedProductId = Number.parseInt(stockProductId, 10);
    const parsedQty = Number.parseInt(stockQuantity, 10);
    if (Number.isNaN(parsedProductId) || parsedProductId <= 0) {
      setError("Selecciona un producto valido.");
      return;
    }
    if (Number.isNaN(parsedQty) || parsedQty <= 0) {
      setError("Cantidad de stock invalida.");
      return;
    }

    const variants = variantsByProduct[parsedProductId] ?? [];
    if (variants.length === 0) {
      setError("El producto seleccionado no tiene variantes para actualizar stock.");
      return;
    }
    if (!selectedVariantIds.length) {
      setError("Selecciona al menos una variante.");
      return;
    }
    const variantIdSet = new Set(selectedVariantIds.map((id) => Number(id)));
    const variantsToUpdate = variants.filter((variant) => variantIdSet.has(Number(variant.id)));
    if (variantsToUpdate.length === 0) {
      setError("Las variantes seleccionadas no son validas para el producto.");
      return;
    }

    setAddingStock(true);
    setError("");
    setStockSuccessMessage("");
    try {
      await Promise.all(
        variantsToUpdate.map((variant) =>
          patchAdminVariant(variant.id, {
            stock: Number(variant.stock ?? 0) + parsedQty
          })
        )
      );
      await loadAll();
      setStockProductId("");
      setStockQuantity("0");
      setStockSuccessMessage(`Stock actualizado en ${variantsToUpdate.length} variante(s).`);
    } catch {
      setError("No se pudo agregar stock al producto.");
    } finally {
      setAddingStock(false);
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

  const productsSorted = useMemo(
    () => [...products].sort((a, b) => String(a.name).localeCompare(String(b.name))),
    [products]
  );

  const productsByCategory = useMemo(() => {
    const grouped: Record<string, AdminProduct[]> = {};
    for (const product of productsSorted) {
      const categoryName = String(product.category || "Sin categoria");
      if (!grouped[categoryName]) {
        grouped[categoryName] = [];
      }
      grouped[categoryName].push(product);
    }
    return grouped;
  }, [productsSorted]);

  const categoryNames = useMemo(
    () => categories.map((category) => category.name).sort((a, b) => a.localeCompare(b)),
    [categories]
  );

  const visibleProducts = useMemo(() => {
    if (catalogCategoryFilter === "all") {
      return productsSorted;
    }
    return productsSorted.filter((product) => String(product.category || "") === catalogCategoryFilter);
  }, [productsSorted, catalogCategoryFilter]);

  const variantOptions = useMemo<VariantOption[]>(() => {
    const rows: VariantOption[] = [];
    for (const product of products) {
      const variants = variantsByProduct[product.id] ?? [];
      for (const variant of variants) {
        rows.push({
          value: String(variant.id),
          label: `${product.name} | ${variant.sku} (${variant.size || "-"} / ${variant.color || "-"})`,
          priceCents: Number(variant.price ?? 0)
        });
      }
    }
    return rows.sort((a, b) => a.label.localeCompare(b.label));
  }, [products, variantsByProduct]);

  return {
    categories,
    productsSorted,
    productsByCategory,
    visibleProducts,
    categoryNames,
    variantsByProduct,
    variantOptions,
    catalogCategoryFilter,
    setCatalogCategoryFilter,
    showAddStockModal,
    setShowAddStockModal,
    stockProductId,
    setStockProductId,
    stockQuantity,
    setStockQuantity,
    addingStock,
    stockSuccessMessage,
    onOpenAddStockModal,
    onConfirmAddStock,
    showCreateProductForm,
    setShowCreateProductForm,
    onCreateProduct,
    showCreateCategoryForm,
    setShowCreateCategoryForm,
    onCreateCategory,
    onDeleteCategory,
    newCategoryName,
    setNewCategoryName,
    creatingCategory,
    savingNew,
    newName,
    setNewName,
    newCategory,
    setNewCategory,
    newDescription,
    setNewDescription,
    newImgUrl,
    setNewImgUrl,
    loading,
    error,
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
    setEditingVariantId
  };
}
