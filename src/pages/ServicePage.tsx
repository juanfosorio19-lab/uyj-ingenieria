import { useParams, Link } from "react-router-dom";
import { ArrowRight, ArrowLeft } from "lucide-react";
import Layout from "@/components/Layout";

interface ServiceData {
  title: string;
  category: string;
  accent: string;
  description: string;
  processes: string[];
  detail: string;
}

const serviceData: Record<string, ServiceData> = {
  "fibra-de-vidrio": {
    title: "Diseño y Fabricación en Fibra de Vidrio (FRP)",
    category: "Ingeniería y Fabricación",
    accent: "#EDCD1F",
    description: "Diseñamos y fabricamos equipos, estanques, ductos, canaletas y piezas especiales en fibra de vidrio reforzado (FRP/GRP) para entornos industriales de alta exigencia. Nuestros productos resisten la corrosión, ácidos y condiciones climáticas extremas, ideales para plantas mineras, químicas y de tratamiento de aguas. Trabajamos con resinas vinilester, isoftálicas y ortoftálicas según el requerimiento técnico.",
    processes: ["Laminado manual y por proyección", "Filament winding", "Moldeo por contacto", "Reparaciones y revestimientos in situ", "Diseño con software CAD", "Piezas especiales a medida"],
    detail: "Proyectos ejecutados en Chile y Perú. Visita técnica sin costo para proyectos en RM.",
  },
  "soldadura-termoplasticos": {
    title: "Soldadura de Termoplásticos",
    category: "Ingeniería y Fabricación",
    accent: "#4A90D9",
    description: "Realizamos uniones profesionales en materiales termoplásticos como PP-R, HDPE y otros polímeros industriales mediante técnicas de polifusión, electrofusión y soldadura por extrusión. Nuestros servicios abarcan desde la instalación completa de sistemas de tuberías hasta reparaciones en plantas en operación.",
    processes: ["Polifusión (butt fusion)", "Electrofusión", "Soldadura por extrusión", "Soldadura con aire caliente", "Prefabricación en taller", "Instalación en terreno"],
    detail: "Personal capacitado bajo estándares DVS y normas internacionales.",
  },
  "tableros-electricos": {
    title: "Diseño y Fabricación de Tableros Eléctricos",
    category: "Ingeniería y Fabricación",
    accent: "#52C878",
    description: "Diseñamos, fabricamos e instalamos tableros eléctricos de control, distribución, fuerza y automatización para aplicaciones industriales. Cada tablero se desarrolla a medida según los requerimientos del proyecto, cumpliendo con normativa SEC y estándares IEC. Nuestro equipo gestiona desde el diseño unifilar hasta la programación de PLC y puesta en marcha.",
    processes: ["Diseño unifilar y de control", "Tableros de distribución BT/MT", "Tableros de automatización PLC", "Pruebas FAT", "Puesta en marcha en terreno", "Certificación SEC"],
    detail: "Componentes de marcas certificadas. Pruebas FAT antes de cada despacho.",
  },
  "maestranza": {
    title: "Maestranza y Fabricaciones Especiales",
    category: "Fabricación Especial",
    accent: "#9B59B6",
    description: "Contamos con capacidad de maestranza para fabricar piezas, partes y prototipos que no se consiguen en el mercado estándar. Fabricamos cables y arneses eléctricos a medida, mecanizados en plásticos y polímeros técnicos, y series cortas de piezas metálicas. Atendemos pedidos puntuales con tiempos de respuesta cortos.",
    processes: ["Fabricación de cables y arneses", "Mecanizado y modificación de plásticos", "Piezas metálicas a pedido", "Prototipos y series cortas", "Adaptaciones de componentes", "Soldadura TIG/MIG"],
    detail: "Ideal para empresas que necesitan repuestos fuera de catálogo o soluciones rápidas.",
  },
  "obras-civiles": {
    title: "Obras Civiles y Remodelación de Oficinas",
    category: "Obras y Construcción",
    accent: "#C4622D",
    description: "Ejecutamos obras civiles menores y proyectos de remodelación para empresas que necesitan habilitar, mejorar o adecuar sus espacios de trabajo. Realizamos desde reparaciones puntuales hasta habilitaciones completas de oficinas. Trabajamos con plazos definidos y presupuesto transparente.",
    processes: ["Pintura de interiores y exteriores", "Instalación de pisos (flotante, cerámica, epóxico)", "Tabiques y divisiones", "Habilitación completa de oficinas", "Reparaciones y mantención", "Cielos, iluminación y terminaciones"],
    detail: "Atendemos empresas en Santiago y regiones. Visita técnica sin costo en RM.",
  },
  "muebles-medida": {
    title: "Muebles a Medida y Carpintería",
    category: "Muebles y Espacios",
    accent: "#A07850",
    description: "Diseñamos y fabricamos muebles a medida para oficinas, bodegas y espacios industriales, con enfoque en funcionalidad y durabilidad. Trabajamos con MDF, melanina y madera natural. Cada proyecto incluye levantamiento en terreno, propuesta de diseño y fabricación e instalación a cargo de nuestro equipo.",
    processes: ["Levantamiento y diseño personalizado", "Corte y mecanizado en taller propio", "Materiales: MDF, melanina, madera natural", "Laminado y acabados", "Ensamble e instalación en sitio", "Escritorios, estanterías, recepciones"],
    detail: "Fabricamos desde una pieza hasta proyectos completos de mobiliario corporativo.",
  },
};

const ServicePage = () => {
  const { slug } = useParams<{ slug: string }>();
  const service = slug ? serviceData[slug] : null;

  if (!service) {
    return (
      <Layout>
        <div className="section-padding text-center">
          <h1 className="font-heading text-3xl font-bold text-foreground mb-4">Servicio no encontrado</h1>
          <Link to="/" className="text-primary hover:underline">Volver al inicio</Link>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <section className="bg-navy section-padding" style={{ borderLeft: `4px solid ${service.accent}` }}>
        <div className="container mx-auto">
          <Link to="/" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-primary mb-6 transition-colors">
            <ArrowLeft className="h-3 w-3" /> Volver al inicio
          </Link>
          <span className="block text-xs font-heading font-semibold uppercase tracking-widest mb-2" style={{ color: service.accent }}>{service.category}</span>
          <h1 className="font-heading text-3xl md:text-5xl font-bold text-navy-foreground uppercase">{service.title}</h1>
        </div>
      </section>

      <section className="section-padding bg-background">
        <div className="container mx-auto max-w-4xl">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
            <div className="lg:col-span-2">
              <h2 className="font-heading text-2xl font-bold text-foreground mb-4 uppercase">Descripción del Servicio</h2>
              <p className="text-muted-foreground leading-relaxed mb-8">{service.description}</p>
              <h3 className="font-heading text-xl font-bold text-foreground mb-3 uppercase">Procesos y Capacidades</h3>
              <ul className="space-y-2 mb-8">
                {service.processes.map((p, i) => (
                  <li key={i} className="flex items-start gap-3 text-muted-foreground">
                    <span className="mt-1.5 w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: service.accent }} />
                    {p}
                  </li>
                ))}
              </ul>
              <p className="text-sm text-muted-foreground italic border-l-2 pl-4" style={{ borderColor: service.accent }}>{service.detail}</p>
            </div>
            <div>
              <div className="sticky top-24 p-6 bg-card border border-border rounded" style={{ borderTop: `4px solid ${service.accent}` }}>
                <h3 className="font-heading text-lg font-bold text-foreground mb-3 uppercase">¿Necesita este servicio?</h3>
                <p className="text-sm text-muted-foreground mb-4">Solicite una cotización sin compromiso. Le respondemos en menos de 24 horas.</p>
                <Link to="/cotizar" className="flex items-center justify-center gap-2 w-full px-6 py-3 font-heading font-bold rounded hover:opacity-90 transition-opacity" style={{ backgroundColor: service.accent, color: "#fff" }}>
                  Solicitar Cotización <ArrowRight className="h-4 w-4" />
                </Link>
                <div className="mt-6 pt-4 border-t border-border">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    También puede escribirnos a{" "}
                    <a href="mailto:info@uingenieria.com" className="text-primary hover:underline">info@uingenieria.com</a>
                    {" "}o llamarnos al{" "}
                    <a href="tel:+56972800950" className="text-primary hover:underline">+56 9 7280 0950</a>
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="section-padding bg-dark text-center">
        <div className="container mx-auto max-w-2xl">
          <h2 className="font-heading text-2xl md:text-3xl font-bold text-dark-foreground mb-4 uppercase">Conversemos sobre su proyecto</h2>
          <p className="text-muted-foreground mb-6">En U&J combinamos ingeniería, fabricación y servicio en terreno para entregarle la mejor solución.</p>
          <Link to="/cotizar" className="inline-flex items-center gap-2 px-8 py-3.5 bg-primary text-primary-foreground font-heading font-bold rounded hover:opacity-90 transition-opacity">
            Cotizar ahora <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </section>
    </Layout>
  );
};

export default ServicePage;
