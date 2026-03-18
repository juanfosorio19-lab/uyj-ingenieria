import { useState } from "react";
import { ArrowRight, CheckCircle } from "lucide-react";
import Layout from "@/components/Layout";

const serviceOptions = [
  "Obras Civiles y Remodelación",
  "Muebles a Medida",
  "Maestranza y Fabricaciones Especiales",
  "Combinación de servicios",
  "No estoy seguro / consulta general",
];

const FORMSPREE_ENDPOINT = "https://formspree.io/f/info@uingenieria.com";

const QuotePage = () => {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    const form = e.currentTarget;
    const data = new FormData(form);
    try {
      const res = await fetch(FORMSPREE_ENDPOINT, {
        method: "POST",
        body: data,
        headers: { Accept: "application/json" },
      });
      if (res.ok) {
        setSubmitted(true);
      } else {
        setError("Hubo un error al enviar. Por favor escríbanos directamente a info@uingenieria.com");
      }
    } catch {
      setError("Error de conexión. Por favor escríbanos a info@uingenieria.com");
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <Layout>
        <section className="section-padding bg-background min-h-[60vh] flex items-center justify-center">
          <div className="text-center max-w-md">
            <CheckCircle className="h-16 w-16 text-primary mx-auto mb-4" />
            <h1 className="font-heading text-3xl font-bold text-foreground mb-3 uppercase">¡Solicitud enviada!</h1>
            <p className="text-muted-foreground mb-2">Le contactaremos en menos de 24 horas hábiles.</p>
            <p className="text-sm text-muted-foreground">
              ¿Urgente? Llámenos al{" "}
              <a href="tel:+56972800950" className="text-primary hover:underline font-medium">+56 9 7280 0950</a>
            </p>
          </div>
        </section>
      </Layout>
    );
  }

  return (
    <Layout>
      <section className="bg-navy section-padding">
        <div className="container mx-auto text-center">
          <p className="text-primary font-heading font-bold text-xs tracking-widest uppercase mb-3">Sin compromiso</p>
          <h1 className="font-heading text-3xl md:text-4xl font-bold text-navy-foreground mb-3 uppercase">
            Solicitar Cotización
          </h1>
          <p className="text-muted-foreground max-w-xl mx-auto">
            Complete el formulario y le entregaremos una propuesta a medida. Respuesta en menos de 24 horas.
          </p>
        </div>
      </section>

      <section className="section-padding bg-background">
        <div className="container mx-auto max-w-2xl">
          {error && (
            <div className="mb-6 p-4 bg-destructive/10 border border-destructive/30 rounded text-sm text-destructive">{error}</div>
          )}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Nombre completo *</label>
                <input name="nombre" type="text" required className="w-full px-4 py-2.5 border border-input rounded bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="Juan Pérez" />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Empresa</label>
                <input name="empresa" type="text" className="w-full px-4 py-2.5 border border-input rounded bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="Empresa S.A." />
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Correo electrónico *</label>
                <input name="email" type="email" required className="w-full px-4 py-2.5 border border-input rounded bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="correo@empresa.com" />
              </div>
              <div>
                <label className="block text-sm font-medium text-foreground mb-1.5">Teléfono</label>
                <input name="telefono" type="tel" className="w-full px-4 py-2.5 border border-input rounded bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring" placeholder="+56 9 1234 5678" />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Servicio requerido *</label>
              <select name="servicio" required className="w-full px-4 py-2.5 border border-input rounded bg-card text-foreground focus:outline-none focus:ring-2 focus:ring-ring" defaultValue="">
                <option value="" disabled>Seleccione un servicio</option>
                {serviceOptions.map((opt) => (<option key={opt} value={opt}>{opt}</option>))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">¿Tiene plazo definido?</label>
              <div className="flex gap-6">
                {["Sí", "No", "Por definir"].map((opt) => (
                  <label key={opt} className="flex items-center gap-2 text-sm text-muted-foreground cursor-pointer">
                    <input type="radio" name="plazo" value={opt} className="accent-primary" /> {opt}
                  </label>
                ))}
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-foreground mb-1.5">Descripción del proyecto *</label>
              <textarea name="descripcion" required rows={5} className="w-full px-4 py-2.5 border border-input rounded bg-card text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring resize-y" placeholder="Describa brevemente su necesidad: qué requiere, espacio aproximado, plazos, ubicación..." />
            </div>
            <button type="submit" disabled={loading} className="inline-flex items-center gap-2 px-8 py-3.5 bg-primary text-primary-foreground font-heading font-bold rounded hover:opacity-90 transition-opacity disabled:opacity-50">
              {loading ? "Enviando..." : "Enviar solicitud"}
              {!loading && <ArrowRight className="h-4 w-4" />}
            </button>
            <p className="text-xs text-muted-foreground mt-2">
              También puede contactarnos en{" "}
              <a href="mailto:info@uingenieria.com" className="text-primary hover:underline">info@uingenieria.com</a>
              {" "}o al{" "}
              <a href="tel:+56972800950" className="text-primary hover:underline">+56 9 7280 0950</a>
            </p>
          </form>
        </div>
      </section>
    </Layout>
  );
};

export default QuotePage;
