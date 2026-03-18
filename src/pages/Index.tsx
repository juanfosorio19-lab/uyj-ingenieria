import { Link } from "react-router-dom";
import { ArrowRight, Shield, Zap, Wrench, Cog, Building2, Sofa } from "lucide-react";
import Layout from "@/components/Layout";
import { IMAGES } from "@/lib/images";

const services = [
  { icon: Shield,    title: "Fibra de Vidrio (FRP)",         desc: "Diseño y fabricación de estanques, lavadores y piezas especiales en FRP para minería e industria.",         href: "/servicios/fibra-de-vidrio",         category: "Ingeniería y Fabricación", accent: "#EDCD1F" },
  { icon: Zap,       title: "Soldadura de Termoplásticos",   desc: "Instalación y unión de tuberías PP-R, HDPE y sistemas de polifusión para aplicaciones industriales.",       href: "/servicios/soldadura-termoplasticos", category: "Ingeniería y Fabricación", accent: "#4A90D9" },
  { icon: Wrench,    title: "Tableros Eléctricos",           desc: "Diseño, fabricación e instalación de tableros de control, fuerza y automatización bajo normativa SEC.",    href: "/servicios/tableros-electricos",     category: "Ingeniería y Fabricación", accent: "#52C878" },
  { icon: Cog,       title: "Maestranza y Fabricaciones",    desc: "Cables a medida, mecanizados en plásticos, piezas metálicas y series cortas para necesidades especiales.", href: "/servicios/maestranza",              category: "Fabricación Especial",     accent: "#9B59B6" },
  { icon: Building2, title: "Obras Civiles y Remodelación",  desc: "Habilitación, remodelación y mantención de oficinas e instalaciones. Plazos reales, sin intermediarios.",  href: "/servicios/obras-civiles",           category: "Obras y Construcción",     accent: "#C4622D" },
  { icon: Sofa,      title: "Muebles a Medida",              desc: "Muebles para oficinas, bodegas y espacios industriales. Diseño, fabricación e instalación incluida.",       href: "/servicios/muebles-medida",          category: "Muebles y Espacios",       accent: "#A07850" },
];

const stats = [
  { number: "26+",  label: "Proyectos completados" },
  { number: "+20",  label: "Colaboradores" },
  { number: "2",    label: "Países" },
  { number: "2021", label: "Año de fundación" },
];

const whyUs = [
  { title: "Multidisciplinario",        desc: "Ingeniería, fabricación y construcción bajo un mismo equipo. Sin rotar entre proveedores." },
  { title: "Experiencia en terreno",    desc: "Proyectos ejecutados en Chile y Perú en entornos industriales de alta exigencia." },
  { title: "Plazos que se cumplen",     desc: "Comprometemos fechas reales. El proyecto termina cuando dijimos, sin excusas." },
  { title: "Equipo propio en terreno",  desc: "No subcontratamos el trabajo central. Nuestros técnicos ejecutan cada proyecto." },
];

const projects = [
  { img: IMAGES.proyectoAnclo,    name: "Proyecto Anclo America", category: "FRP · Minería",          alt: "Proyecto Anclo America fabricación FRP ejecutado por U&J Ingeniería Santiago Chile" },
  { img: IMAGES.proyectoEssbio,   name: "Proyecto Essbio",        category: "Obras Civiles",           alt: "Proyecto Essbio obras civiles ejecutado por U&J Ingeniería Chile" },
  { img: IMAGES.proyectoPeru,     name: "Proyecto Perú",          category: "FRP · Internacional",     alt: "Proyecto en Perú fibra de vidrio U&J Ingeniería" },
  { img: IMAGES.proyectoTortolas, name: "Proyecto Las Tórtolas",  category: "Maestranza",              alt: "Proyecto Las Tórtolas maestranza U&J Ingeniería Santiago Chile" },
];

const Index = () => (
  <Layout>
    {/* Hero */}
    <section className="relative min-h-[90vh] flex items-center" aria-label="U&J Ingeniería e Instalaciones Spa">
      <div className="absolute inset-0">
        <img src={IMAGES.hero} alt="Taller de ingeniería y fabricación industrial U&J — FRP, tableros eléctricos, obras civiles Santiago Chile" className="w-full h-full object-cover" loading="eager" fetchPriority="high" />
        <div className="absolute inset-0 bg-dark/80" />
      </div>
      <div className="relative container mx-auto px-4">
        <div className="max-w-3xl">
          <p className="text-primary font-heading font-bold text-sm tracking-widest uppercase mb-4 animate-fade-in flex items-center gap-3">
            <span className="w-8 h-0.5 bg-primary inline-block" aria-hidden="true" />
            Santiago, Chile · Perú
          </p>
          <h1 className="font-heading text-5xl md:text-6xl lg:text-7xl font-bold text-dark-foreground leading-none mb-6 animate-fade-in-up uppercase">
            INGENIERÍA,<br />FABRICACIÓN Y<br /><span className="text-gradient-gold">CONSTRUCCIÓN.</span>
          </h1>
          <p className="text-lg md:text-xl text-muted-foreground max-w-2xl mb-8 animate-fade-in-up" style={{ animationDelay: "0.2s" }}>
            Desde fibra de vidrio y tableros eléctricos hasta obras civiles y muebles industriales.
            Todo en un solo proveedor, con la calidad que la industria exige.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 animate-fade-in-up" style={{ animationDelay: "0.4s" }}>
            <Link to="/cotizar" className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-primary text-primary-foreground font-heading font-bold rounded hover:opacity-90 transition-opacity text-base">
              Solicitar Cotización <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
            <Link to="/nosotros" className="inline-flex items-center justify-center gap-2 px-8 py-4 border border-primary text-primary font-heading font-bold rounded hover:bg-primary hover:text-primary-foreground transition-colors text-base">
              Conocer más
            </Link>
          </div>
        </div>
      </div>
    </section>

    {/* Service strip */}
    <div className="bg-primary py-4" aria-hidden="true">
      <div className="container mx-auto px-4">
        <div className="flex flex-wrap justify-center gap-x-6 gap-y-2">
          {["FRP & Fibra de Vidrio", "Termoplásticos", "Tableros Eléctricos", "Maestranza", "Obras Civiles", "Muebles a Medida"].map((s) => (
            <span key={s} className="font-heading font-bold text-sm uppercase tracking-widest text-primary-foreground">· {s}</span>
          ))}
        </div>
      </div>
    </div>

    {/* Stats */}
    <div className="bg-navy" aria-label="Estadísticas U&J Ingeniería">
      <div className="container mx-auto px-4 py-10">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 divide-x divide-navy-foreground/10">
          {stats.map((s, i) => (
            <div key={i} className="text-center px-4">
              <div className="font-heading text-4xl md:text-5xl font-bold text-primary">{s.number}</div>
              <div className="text-xs text-muted-foreground uppercase tracking-widest mt-1 font-medium">{s.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>

    {/* Services — 6 cards */}
    <section className="section-padding bg-background" aria-labelledby="servicios-heading">
      <div className="container mx-auto">
        <div className="text-center mb-12">
          <p className="text-primary font-heading font-bold text-xs tracking-widest uppercase mb-3">Qué hacemos</p>
          <h2 id="servicios-heading" className="font-heading text-3xl md:text-5xl font-bold text-foreground mb-3 uppercase">
            Seis soluciones.<br />Un solo equipo.
          </h2>
          <div className="w-16 h-1 bg-primary mx-auto mt-4" aria-hidden="true" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {services.map((s, i) => (
            <Link key={s.href} to={s.href} className="group p-7 bg-card border-t-4 border-x border-b border-border rounded hover:shadow-xl hover:-translate-y-1 transition-all" style={{ borderTopColor: s.accent }} aria-label={`Ver servicio: ${s.title}`}>
              <div className="flex items-start justify-between mb-5">
                <div className="inline-flex items-center justify-center w-12 h-12 rounded bg-secondary" aria-hidden="true">
                  <s.icon className="h-6 w-6 text-primary" />
                </div>
                <span className="font-heading text-6xl font-bold opacity-10 text-foreground leading-none" aria-hidden="true">{String(i + 1).padStart(2, "0")}</span>
              </div>
              <span className="block text-xs font-heading font-semibold text-primary mb-1 uppercase tracking-wider">{s.category}</span>
              <h3 className="font-heading text-lg font-bold text-foreground mb-2 group-hover:text-primary transition-colors uppercase">{s.title}</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">{s.desc}</p>
              <span className="inline-flex items-center gap-1 mt-4 text-sm font-medium text-primary opacity-0 group-hover:opacity-100 transition-opacity" aria-hidden="true">
                Ver servicio <ArrowRight className="h-3 w-3" />
              </span>
            </Link>
          ))}
        </div>
      </div>
    </section>

    {/* Projects */}
    <section className="section-padding bg-navy" aria-labelledby="proyectos-heading">
      <div className="container mx-auto">
        <div className="text-center mb-12">
          <p className="text-primary font-heading font-bold text-xs tracking-widest uppercase mb-3">Portafolio</p>
          <h2 id="proyectos-heading" className="font-heading text-3xl md:text-5xl font-bold text-navy-foreground mb-3 uppercase">Proyectos realizados</h2>
          <div className="w-16 h-1 bg-primary mx-auto mt-4" aria-hidden="true" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {projects.map((p, i) => (
            <article key={i} className="group relative overflow-hidden rounded bg-dark aspect-square">
              <img src={p.img} alt={p.alt} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" />
              <div className="absolute inset-0 bg-gradient-to-t from-dark/90 via-dark/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="absolute bottom-0 left-0 right-0 p-4 translate-y-full group-hover:translate-y-0 transition-transform duration-300">
                <span className="block text-xs text-primary font-heading uppercase tracking-widest mb-1">{p.category}</span>
                <h3 className="font-heading font-bold text-white text-sm uppercase">{p.name}</h3>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>

    {/* Clients */}
    <section className="py-16 bg-background" aria-labelledby="clientes-heading">
      <div className="container mx-auto px-4">
        <div className="text-center mb-10">
          <p className="text-primary font-heading font-bold text-xs tracking-widest uppercase mb-3">Empresas que confían en nosotros</p>
          <h2 id="clientes-heading" className="font-heading text-2xl md:text-3xl font-bold text-foreground uppercase">Nuestros Clientes</h2>
          <div className="w-16 h-1 bg-primary mx-auto mt-4" aria-hidden="true" />
        </div>
        <div className="flex flex-wrap justify-center items-center gap-8 md:gap-12">
          {IMAGES.clientes.map((url, i) => (
            <div key={i} className="flex items-center justify-center w-24 h-24 grayscale hover:grayscale-0 opacity-60 hover:opacity-100 transition-all duration-300">
              <img src={url} alt={`Cliente ${i + 1} de U&J Ingeniería`} className="max-w-full max-h-full object-contain" loading="lazy" />
            </div>
          ))}
        </div>
      </div>
    </section>

    {/* Why U&J */}
    <section className="section-padding bg-navy" aria-labelledby="porque-heading">
      <div className="container mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
          <div>
            <p className="text-primary font-heading font-bold text-xs tracking-widest uppercase mb-3">Por qué elegirnos</p>
            <h2 id="porque-heading" className="font-heading text-3xl md:text-5xl font-bold text-navy-foreground mb-4 uppercase">Un solo proveedor<br />para todo.</h2>
            <div className="w-16 h-1 bg-primary mb-6" aria-hidden="true" />
            <p className="text-muted-foreground leading-relaxed mb-8 max-w-md">
              En U&J coordinamos ingeniería, construcción y fabricación bajo un mismo equipo. No intermediarios, no subcontratos. Del diseño a la entrega, somos responsables de cada etapa.
            </p>
            <Link to="/nosotros" className="inline-flex items-center gap-2 px-6 py-3 border border-primary text-primary font-heading font-bold rounded hover:bg-primary hover:text-primary-foreground transition-colors">
              Conocer nuestra historia <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </Link>
          </div>
          <div className="space-y-4">
            {whyUs.map((item, i) => (
              <div key={i} className="flex gap-4 p-5 rounded border border-navy-foreground/10 bg-navy-foreground/5 hover:border-primary/40 transition-colors">
                <div className="shrink-0 w-10 h-10 flex items-center justify-center rounded bg-primary text-primary-foreground font-heading font-bold text-lg" aria-hidden="true">{i + 1}</div>
                <div>
                  <h3 className="font-heading text-base font-bold text-navy-foreground mb-1 uppercase">{item.title}</h3>
                  <p className="text-sm text-muted-foreground leading-relaxed">{item.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>

    {/* CTA */}
    <section className="bg-primary py-20 text-center" aria-labelledby="cta-heading">
      <div className="container mx-auto max-w-2xl px-4">
        <h2 id="cta-heading" className="font-heading text-3xl md:text-4xl font-bold text-primary-foreground mb-4 uppercase">¿Tiene un proyecto en mente?</h2>
        <p className="text-primary-foreground/80 mb-8 text-lg">Cuéntenos su necesidad. Cotización sin compromiso, respuesta en 24 horas.</p>
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link to="/cotizar" className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-dark text-dark-foreground font-heading font-bold rounded hover:opacity-90 transition-opacity">
            Solicitar Cotización <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
          <a href="tel:+56972800950" className="inline-flex items-center justify-center gap-2 px-8 py-4 border-2 border-dark text-primary-foreground font-heading font-bold rounded hover:bg-dark hover:text-dark-foreground transition-colors">
            +56 9 7280 0950
          </a>
        </div>
      </div>
    </section>
  </Layout>
);

export default Index;
