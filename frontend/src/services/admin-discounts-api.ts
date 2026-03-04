import { http } from "./http";

export type AdminDiscount = {
  id: number;
  name: string;
  type: "percent" | "fixed";
  value: number;
  scope: "all" | "category" | "product" | "product_list";
  category_id: number | null;
  product_id: number | null;
  is_active: boolean;
  starts_at: string | null;
  ends_at: string | null;
  product_ids: number[];
};

export async function listAdminDiscounts(): Promise<AdminDiscount[]> {
  const response = await http.get<{ data: AdminDiscount[] }>("/discounts");
  return response.data.data;
}

export async function createAdminDiscount(payload: {
  name: string;
  type: "percent" | "fixed";
  value: number;
  scope: "all" | "category" | "product" | "product_list";
  category_id?: number | null;
  product_id?: number | null;
  is_active?: boolean;
  starts_at?: string | null;
  ends_at?: string | null;
  product_ids?: number[];
}): Promise<AdminDiscount> {
  const response = await http.post<{ data: AdminDiscount }>("/discounts", payload);
  return response.data.data;
}

export async function patchAdminDiscount(
  discountId: number,
  payload: Partial<{
    name: string;
    type: "percent" | "fixed";
    value: number;
    scope: "all" | "category" | "product" | "product_list";
    category_id: number | null;
    product_id: number | null;
    is_active: boolean;
    starts_at: string | null;
    ends_at: string | null;
    product_ids: number[];
  }>
): Promise<AdminDiscount> {
  const response = await http.patch<{ data: AdminDiscount }>(`/discounts/${discountId}`, payload);
  return response.data.data;
}

export async function deleteAdminDiscount(discountId: number): Promise<void> {
  await http.delete(`/discounts/${discountId}`);
}
