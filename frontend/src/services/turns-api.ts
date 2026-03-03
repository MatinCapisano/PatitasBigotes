import { http } from "./http";

export async function createTurnRequest(payload: { scheduled_at: string | null; notes: string }) {
  const response = await http.post("/turns", payload);
  return response.data;
}

export type AdminTurn = {
  id: number;
  status: "pending" | "confirmed" | "cancelled";
  scheduled_at: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  customer: {
    id: number | null;
    first_name: string | null;
    last_name: string | null;
    phone: string | null;
  };
};

export async function listAdminTurns(status?: "pending" | "confirmed" | "cancelled") {
  const response = await http.get<{ data: AdminTurn[] }>("/admin/turns", {
    params: status ? { status } : undefined
  });
  return response.data.data;
}

export async function updateAdminTurnStatus(turnId: number, status: "confirmed" | "cancelled") {
  const response = await http.patch<{ data: AdminTurn }>(`/admin/turns/${turnId}/status`, { status });
  return response.data.data;
}
