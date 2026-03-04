import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { addToCart } from "../../../lib/cart-storage";
import type { StorefrontProductDetail } from "../../../types";
import { fetchStorefrontProductById } from "../../../services/storefront-api";

export function useProductDetailPage() {
  const params = useParams();
  const navigate = useNavigate();
  const [product, setProduct] = useState<StorefrontProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null);

  useEffect(() => {
    async function run() {
      setLoading(true);
      setError("");
      try {
        const id = Number(params.productId);
        const payload = await fetchStorefrontProductById(id);
        setProduct(payload.data);
        setSelectedVariantId(payload.data.options[0]?.variant_id ?? null);
      } catch {
        setError("No se pudo cargar el producto.");
      } finally {
        setLoading(false);
      }
    }
    void run();
  }, [params.productId]);

  const selectedOption =
    product?.options.find((option) => option.variant_id === selectedVariantId) ?? product?.options[0];
  const currentImageUrl =
    selectedOption?.effective_img_url ?? selectedOption?.img_url ?? product?.img_url ?? null;

  function onBuy() {
    if (!product) return;
    if (!selectedOption || !selectedOption.in_stock) return;
    addToCart({
      product_id: product.id,
      product_name: product.name,
      variant_id: selectedOption.variant_id,
      option_label: selectedOption.label,
      unit_price: selectedOption.price,
      quantity: 1,
      img_url: selectedOption.effective_img_url ?? selectedOption.img_url ?? product.img_url
    });
    const goCheckout = window.confirm(
      "Producto agregado al carrito.\nAceptar: Finalizar compra\nCancelar: Seguir comprando"
    );
    if (goCheckout) {
      navigate("/checkout");
      return;
    }
    navigate("/home");
  }

  return {
    product,
    loading,
    error,
    selectedVariantId,
    setSelectedVariantId,
    selectedOption,
    currentImageUrl,
    onBuy
  };
}
