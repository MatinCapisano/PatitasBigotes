export type CartItem = {
  product_id: number;
  product_name: string;
  variant_id: number;
  option_label: string;
  unit_price: number;
  quantity: number;
  img_url: string | null;
};

const CART_KEY = "pb_cart_items";

export function readCart(): CartItem[] {
  try {
    const raw = localStorage.getItem(CART_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed as CartItem[];
  } catch {
    return [];
  }
}

export function writeCart(items: CartItem[]): void {
  localStorage.setItem(CART_KEY, JSON.stringify(items));
}

export function addToCart(item: CartItem): void {
  const current = readCart();
  const existing = current.find(
    (row) => row.product_id === item.product_id && row.variant_id === item.variant_id
  );
  if (existing) {
    existing.quantity += item.quantity;
  } else {
    current.push(item);
  }
  writeCart(current);
}

export function cartCount(): number {
  return readCart().reduce((acc, item) => acc + Number(item.quantity || 0), 0);
}

export function clearCart(): void {
  localStorage.removeItem(CART_KEY);
}
