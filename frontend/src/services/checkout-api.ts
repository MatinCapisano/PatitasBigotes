import type { CartItem } from "../lib/cart-storage";
import { http } from "./http";

export type CheckoutPaymentMethod = "bank_transfer" | "mercadopago" | "cash";

type GuestCustomer = {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
};

type OrderData = {
  id: number;
  status: string;
  total_amount: number;
  items: Array<{ id: number }>;
};

type PaymentData = {
  id: number;
  method: "bank_transfer" | "mercadopago";
  status: string;
  amount: number;
  currency: string;
  provider_payload_data?: {
    checkout?: {
      checkout_url?: string | null;
      init_point?: string | null;
      sandbox_init_point?: string | null;
    };
  };
};

type OrderEnvelope = {
  data: {
    id: number;
    status: string;
    total_amount: number;
    items: Array<{ id: number }>;
  };
  meta?: {
    created?: boolean;
  };
};

type GuestCheckoutEnvelope = {
  data: {
    order: OrderData;
    payment?: PaymentData;
  };
};

type CheckoutSubmitResult = {
  order: OrderData;
  payment: PaymentData | null;
};

export function getMercadoPagoCheckoutUrl(payment: PaymentData | null): string | null {
  if (!payment || payment.method !== "mercadopago") {
    return null;
  }
  const checkout = payment.provider_payload_data?.checkout;
  const checkoutUrl =
    checkout?.checkout_url?.trim() ||
    checkout?.init_point?.trim() ||
    checkout?.sandbox_init_point?.trim();
  return checkoutUrl || null;
}

function buildIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return `guest_checkout_${crypto.randomUUID()}`;
  }
  return `guest_checkout_${Date.now()}_${Math.random().toString(16).slice(2)}`;
}

function toCheckoutItems(items: CartItem[]) {
  return items.map((item) => ({
    variant_id: item.variant_id,
    quantity: item.quantity
  }));
}

export async function submitGuestCheckoutFromCart(
  items: CartItem[],
  customer: GuestCustomer,
  paymentMethod: CheckoutPaymentMethod
): Promise<CheckoutSubmitResult> {
  const payload = {
    customer,
    items: toCheckoutItems(items),
    website: "",
    payment_method: paymentMethod === "cash" ? null : paymentMethod
  };
  const response = await http.post<GuestCheckoutEnvelope>("/checkout/guest", payload, {
    headers: {
      "Idempotency-Key": buildIdempotencyKey()
    }
  });
  return {
    order: response.data.data.order,
    payment: response.data.data.payment ?? null
  };
}

async function getDraftOrder(): Promise<OrderEnvelope["data"]> {
  const response = await http.get<OrderEnvelope>("/orders/draft");
  return response.data.data;
}

async function clearDraftItems(itemIds: number[]) {
  for (const itemId of itemIds) {
    await http.delete(`/orders/draft/items/${itemId}`);
  }
}

export async function submitAuthenticatedCheckoutFromCart(
  items: CartItem[],
  paymentMethod: CheckoutPaymentMethod
): Promise<CheckoutSubmitResult> {
  const draft = await getDraftOrder();
  const itemIds = Array.isArray(draft.items) ? draft.items.map((row) => Number(row.id)).filter(Number.isFinite) : [];
  if (itemIds.length > 0) {
    await clearDraftItems(itemIds);
  }

  let orderId = draft.id;
  for (const row of items) {
    const response = await http.post<OrderEnvelope>("/orders/draft/items", {
      variant_id: row.variant_id,
      quantity: row.quantity
    });
    orderId = response.data.data.id;
  }

  const submitted = await http.patch<OrderEnvelope>(`/orders/${orderId}/status`, {
    status: "submitted"
  });
  if (paymentMethod === "cash") {
    return { order: submitted.data.data, payment: null };
  }
  const paymentResponse = await http.post<{ data: PaymentData }>(
    `/orders/${orderId}/payments`,
    {
      method: paymentMethod,
      currency: "ARS",
      expires_in_minutes: 60
    },
    {
      headers: {
        "Idempotency-Key": `checkout_payment_${orderId}_${paymentMethod}_${buildIdempotencyKey()}`
      }
    }
  );
  return {
    order: submitted.data.data,
    payment: paymentResponse.data.data
  };
}
