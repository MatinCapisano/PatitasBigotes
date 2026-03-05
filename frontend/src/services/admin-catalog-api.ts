import { http } from "./http";

export type AdminProduct = {
  id: number;
  name: string;
  description: string | null;
  img_url?: string | null;
  min_var_price: number | null;
  category: string | null;
  category_id: number;
  stock: number;
  active: number;
};

export type AdminCategory = {
  id: number;
  name: string;
};

export type AdminVariant = {
  id: number;
  product_id: number;
  sku: string;
  size: string | null;
  color: string | null;
  img_url?: string | null;
  price: number;
  stock: number;
  active: number;
};

export async function listAdminProducts(): Promise<AdminProduct[]> {
  const response = await http.get<{ data: AdminProduct[] }>("/products");
  return response.data.data;
}

export async function listAdminCategories(): Promise<AdminCategory[]> {
  const response = await http.get<{ data: AdminCategory[] }>("/categories");
  return response.data.data;
}

export async function createAdminCategory(payload: { name: string }): Promise<AdminCategory> {
  const response = await http.post<{ data: AdminCategory }>("/categories", payload);
  return response.data.data;
}

export async function deleteAdminCategory(categoryId: number): Promise<AdminCategory> {
  const response = await http.delete<{ data: AdminCategory }>(`/categories/${categoryId}`);
  return response.data.data;
}

export async function createAdminProduct(payload: {
  name: string;
  description: string | null;
  category: string;
  img_url?: string | null;
  active: boolean;
}) {
  const response = await http.post<{ data: AdminProduct }>("/products", payload);
  return response.data.data;
}

export async function deleteAdminProduct(productId: number) {
  const response = await http.delete<{ data: AdminProduct }>(`/products/${productId}`);
  return response.data.data;
}

export async function patchAdminProduct(
  productId: number,
  payload: {
    name?: string;
    description?: string | null;
    category?: string;
    img_url?: string | null;
    active?: boolean;
  }
) {
  const response = await http.patch<{ data: AdminProduct }>(`/products/${productId}`, payload);
  return response.data.data;
}

export async function listProductVariants(productId: number): Promise<AdminVariant[]> {
  const response = await http.get<{ data: AdminVariant[] }>(`/products/${productId}/variants`);
  return response.data.data;
}

export async function patchVariantPrice(variantId: number, price: number): Promise<AdminVariant> {
  const response = await http.patch<{ data: AdminVariant }>(`/variants/${variantId}`, { price });
  return response.data.data;
}

export async function patchAdminVariant(
  variantId: number,
  payload: {
    product_id?: number;
    sku?: string;
    size?: string | null;
    color?: string | null;
    img_url?: string | null;
    price?: number;
    stock?: number;
    active?: boolean;
  }
): Promise<AdminVariant> {
  const response = await http.patch<{ data: AdminVariant }>(`/variants/${variantId}`, payload);
  return response.data.data;
}
