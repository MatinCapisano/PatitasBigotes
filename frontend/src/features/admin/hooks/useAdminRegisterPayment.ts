import { useEffect, useMemo, useState } from "react";
import { searchAdminUsers, type AdminSearchUser } from "../../../services/admin-sales-api";
import { listAdminOrders, registerAdminOrderManualPayment, type AdminOrder } from "../../../services/admin-orders-api";
import { toUserMessage } from "../../../services/http-errors";
import type { AdminSection } from "../types";

function parseMoneyInputToCents(rawValue: string): number {
  const normalized = String(rawValue ?? "").trim();
  if (!normalized) return Number.NaN;
  const digitsOnly = normalized.replace(/\D/g, "");
  if (!digitsOnly) return Number.NaN;
  return Number.parseInt(digitsOnly, 10);
}

function normalizePaymentAmountsForOrder(params: {
  paidRaw: string;
  changeRaw: string;
  totalCents: number;
  method: "cash" | "bank_transfer";
}): { paidCents: number; changeCents: number } | null {
  const paidParsed = parseMoneyInputToCents(params.paidRaw);
  if (Number.isNaN(paidParsed) || paidParsed <= 0) return null;

  const changeParsed = parseMoneyInputToCents(params.changeRaw || "0");
  if (Number.isNaN(changeParsed) || changeParsed < 0) return null;

  const total = Number(params.totalCents || 0);
  if (!Number.isFinite(total) || total < 0) return null;

  const candidates = [
    { paidCents: paidParsed, changeCents: changeParsed },
    { paidCents: paidParsed * 100, changeCents: changeParsed * 100 }
  ];

  for (const candidate of candidates) {
    if (params.method === "cash") {
      if (candidate.paidCents - candidate.changeCents === total) return candidate;
      continue;
    }
    if (candidate.paidCents === total) return candidate;
  }
  return null;
}

export function useAdminRegisterPayment(params: { adminSection: AdminSection }) {
  const { adminSection } = params;
  const [selectedUser, setSelectedUser] = useState<AdminSearchUser | null>(null);
  const [showUserSearch, setShowUserSearch] = useState(false);
  const [searchFirstName, setSearchFirstName] = useState("");
  const [searchLastName, setSearchLastName] = useState("");
  const [searchEmail, setSearchEmail] = useState("");
  const [searchDni, setSearchDni] = useState("");
  const [searchPhone, setSearchPhone] = useState("");
  const [searchLoading, setSearchLoading] = useState(false);
  const [searchError, setSearchError] = useState("");
  const [searchResults, setSearchResults] = useState<AdminSearchUser[]>([]);
  const [pendingSelectedUser, setPendingSelectedUser] = useState<AdminSearchUser | null>(null);

  const [orders, setOrders] = useState<AdminOrder[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");
  const [selectedOrderId, setSelectedOrderId] = useState<number | null>(null);

  const [method, setMethod] = useState<"cash" | "bank_transfer">("cash");
  const [paidAmount, setPaidAmount] = useState("");
  const [changeAmount, setChangeAmount] = useState("0");
  const [paymentRef, setPaymentRef] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showConfirmModal, setShowConfirmModal] = useState(false);

  const selectedOrder = useMemo(
    () => orders.find((row) => row.id === selectedOrderId) ?? null,
    [orders, selectedOrderId]
  );

  useEffect(() => {
    if (adminSection !== "registrar_pago") return;
    if (!showUserSearch) return;
    const hasFilters = [searchFirstName, searchLastName, searchEmail, searchDni, searchPhone]
      .some((value) => value.trim().length > 0);
    if (!hasFilters) {
      setSearchResults([]);
      setSearchError("");
      return;
    }
    const timer = window.setTimeout(async () => {
      setSearchLoading(true);
      setSearchError("");
      try {
        const users = await searchAdminUsers({
          first_name: searchFirstName.trim() || undefined,
          last_name: searchLastName.trim() || undefined,
          email: searchEmail.trim() || undefined,
          dni: searchDni.trim() || undefined,
          phone: searchPhone.trim() || undefined,
          limit: 20
        });
        setSearchResults(users);
      } catch (apiError: unknown) {
        setSearchError(toUserMessage(apiError, "generic"));
      } finally {
        setSearchLoading(false);
      }
    }, 250);
    return () => {
      window.clearTimeout(timer);
    };
  }, [adminSection, showUserSearch, searchFirstName, searchLastName, searchEmail, searchDni, searchPhone]);

  useEffect(() => {
    async function loadSubmittedOrdersForUser() {
      if (!selectedUser) {
        setOrders([]);
        setSelectedOrderId(null);
        return;
      }
      setOrdersLoading(true);
      setOrdersError("");
      try {
        const rows = await listAdminOrders({
          status: "submitted",
          limit: 500,
          sort_by: "created_at",
          sort_dir: "desc"
        });
        const userRows = rows.filter((row) => Number(row.user_id) === Number(selectedUser.id));
        setOrders(userRows);
        setSelectedOrderId(userRows[0]?.id ?? null);
      } catch (apiError: unknown) {
        setOrdersError(toUserMessage(apiError, "generic"));
      } finally {
        setOrdersLoading(false);
      }
    }
    void loadSubmittedOrdersForUser();
  }, [selectedUser]);

  function openUserSearchModal() {
    setShowUserSearch(true);
  }

  function closeUserSearchModal() {
    setShowUserSearch(false);
    setPendingSelectedUser(null);
  }

  function onTogglePendingUser(user: AdminSearchUser, checked: boolean) {
    setPendingSelectedUser(checked ? user : null);
  }

  function onConfirmPendingUser() {
    if (!pendingSelectedUser) return;
    setSelectedUser(pendingSelectedUser);
    setShowUserSearch(false);
    setPendingSelectedUser(null);
    setSearchResults([]);
    setSearchError("");
  }

  function onClearSelectedUser() {
    setSelectedUser(null);
    setSelectedOrderId(null);
    setOrders([]);
    setError("");
    setSuccess("");
  }

  function onOpenConfirm() {
    setError("");
    if (!selectedUser) {
      setError("Selecciona un usuario.");
      return;
    }
    if (!selectedOrder) {
      setError("Selecciona una orden submitted.");
      return;
    }
    const normalized = normalizePaymentAmountsForOrder({
      paidRaw: paidAmount,
      changeRaw: method === "cash" ? changeAmount : "0",
      totalCents: Number(selectedOrder.total_amount || 0),
      method
    });
    if (!normalized) {
      setError("Monto pagado invalido.");
      return;
    }
    const paid = normalized.paidCents;
    const change = normalized.changeCents;
    if (method === "cash") {
      if (paid - change !== Number(selectedOrder.total_amount || 0)) {
        setError("Monto pagado menos vuelto debe ser igual al total de la orden.");
        return;
      }
    } else {
      if (!paymentRef.trim()) {
        setError("La referencia de pago es obligatoria para transferencia.");
        return;
      }
      if (paid !== Number(selectedOrder.total_amount || 0)) {
        setError("Monto pagado debe coincidir con el total de la orden.");
        return;
      }
    }
    setShowConfirmModal(true);
  }

  async function onConfirmPayment() {
    if (!selectedOrder) return;
    if (saving) return;
    setSaving(true);
    setError("");
    setSuccess("");
    const normalized = normalizePaymentAmountsForOrder({
      paidRaw: paidAmount,
      changeRaw: method === "cash" ? changeAmount : "0",
      totalCents: Number(selectedOrder.total_amount || 0),
      method
    });
    if (!normalized) {
      setError("Monto pagado invalido.");
      setSaving(false);
      return;
    }
    try {
      const result = await registerAdminOrderManualPayment({
        order_id: selectedOrder.id,
        method,
        paid_amount: normalized.paidCents,
        change_amount: method === "cash" ? normalized.changeCents : undefined,
        payment_ref: paymentRef.trim() || undefined
      });
      setSuccess(`Pago registrado. Orden #${result.order.id} ahora en estado ${result.order.status}.`);
      setShowConfirmModal(false);
      setPaidAmount("");
      setChangeAmount("0");
      setPaymentRef("");
      setOrders((prev) => prev.filter((order) => order.id !== result.order.id));
      setSelectedOrderId(null);
    } catch (apiError: unknown) {
      setError(toUserMessage(apiError, "generic"));
    } finally {
      setSaving(false);
    }
  }

  return {
    selectedUser,
    onClearSelectedUser,
    showUserSearch,
    openUserSearchModal,
    closeUserSearchModal,
    searchFirstName,
    setSearchFirstName,
    searchLastName,
    setSearchLastName,
    searchEmail,
    setSearchEmail,
    searchDni,
    setSearchDni,
    searchPhone,
    setSearchPhone,
    searchLoading,
    searchError,
    searchResults,
    pendingSelectedUser,
    onTogglePendingUser,
    onConfirmPendingUser,
    orders,
    ordersLoading,
    ordersError,
    selectedOrderId,
    setSelectedOrderId,
    selectedOrder,
    method,
    setMethod,
    paidAmount,
    setPaidAmount,
    changeAmount,
    setChangeAmount,
    paymentRef,
    setPaymentRef,
    saving,
    error,
    success,
    showConfirmModal,
    setShowConfirmModal,
    onOpenConfirm,
    onConfirmPayment
  };
}
