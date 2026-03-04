import { contactInfo } from "../features/contact";

export function ContactPage() {
  return (
    <section>
      <h1 className="page-title">Contacto</h1>
      <p className="page-subtitle">Escribinos para compras, seguimiento de pedidos y consultas.</p>
      <div className="card">
        <p>
          <strong>WhatsApp:</strong> {contactInfo.whatsapp}
        </p>
        <p>
          <strong>Email:</strong> {contactInfo.email}
        </p>
        <p>
          <strong>Horario:</strong> {contactInfo.hours}
        </p>
      </div>
    </section>
  );
}
