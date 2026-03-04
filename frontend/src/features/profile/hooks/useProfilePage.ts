import { useEffect, useState, type FormEvent } from "react";
import type { MyOrder, MyProfile } from "../../../types";
import { getMyOrders, getMyProfile, updateMyProfile } from "../../../services/auth-api";
import { toUserMessage } from "../../../services/http-errors";

export function useProfilePage() {
  const [section, setSection] = useState<"summary" | "history" | "edit">("summary");
  const [profile, setProfile] = useState<MyProfile | null>(null);
  const [orders, setOrders] = useState<MyOrder[]>([]);
  const [ordersLoading, setOrdersLoading] = useState(false);
  const [ordersError, setOrdersError] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");

  async function loadProfile() {
    setLoading(true);
    setError("");
    try {
      const data = await getMyProfile();
      setProfile(data);
      setFirstName(data.first_name || "");
      setLastName(data.last_name || "");
      setPhone(data.phone || "");
      setEmail(data.email || "");
    } catch (apiError: unknown) {
      setError(toUserMessage(apiError, "profile"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadProfile();
  }, []);

  useEffect(() => {
    async function loadOrders() {
      if (section !== "history") return;
      setOrdersLoading(true);
      setOrdersError("");
      try {
        const data = await getMyOrders();
        setOrders(data);
      } catch (apiError: unknown) {
        setOrdersError(toUserMessage(apiError, "profile"));
      } finally {
        setOrdersLoading(false);
      }
    }
    void loadOrders();
  }, [section]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (!profile) return;
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const previousEmail = profile.email;
      const result = await updateMyProfile({
        first_name: firstName.trim(),
        last_name: lastName.trim(),
        phone: phone.trim(),
        email: email.trim()
      });
      setProfile(result.data);
      const verificationSent = Boolean((result.meta as Record<string, unknown>).verification_email_sent);
      if (verificationSent && previousEmail.trim().toLowerCase() !== email.trim().toLowerCase()) {
        setSuccess("Perfil actualizado. Como cambiaste el email, te enviamos una verificacion a tu nuevo correo.");
      } else {
        setSuccess("Perfil actualizado.");
      }
    } catch (apiError: unknown) {
      setError(toUserMessage(apiError, "profile"));
    } finally {
      setSaving(false);
    }
  }

  return {
    section,
    setSection,
    profile,
    orders,
    ordersLoading,
    ordersError,
    loading,
    saving,
    error,
    success,
    firstName,
    setFirstName,
    lastName,
    setLastName,
    phone,
    setPhone,
    email,
    setEmail,
    onSubmit
  };
}
