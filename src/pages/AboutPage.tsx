import Layout from "@/components/Layout";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { IMAGES } from "@/lib/images";

const values = [
  { title: "Compromiso con el resultado", desc: "Cada proyecto se entrega según lo prometido: plazo, precio y calidad acordados desde el inicio." },
  { title: "Diseño + ejecución propia", desc: "Diseñamos y ejecutamos con nuestro equipo. Sin subcontratos, sin intermediarios, sin sorpresas." },
  { title: "Orientado al cliente", desc: "Nos adaptamos a sus tiempos y necesidades. Desde una reparación puntual hasta un proyecto completo." },
];

const AboutPage = () => (
  <Layout>
    {/* Hero */}
    <section className="bg-navy section-padding">
      <div className="container mx-auto">
        <p className="text-primary font-heading font-bold text-xs tracking-widest uppercase mb-3">Sobre nosotros</p>
        <h1 className="font-heading text-3xl md:text-5xl font-bold text-navy-foreground mb-4 uppercase">
          Quiénes somos<br />y por qué lo hacemos.
        </h1>
        <div className="w-16 h-1 bg-primary mb-6" />
        <p className="text-muted-foreground max-w-2xl text-lg leading-relaxed">
          U&J es una empresa chilena que diseña, fabrica y ejecuta soluciones para espacios de trabajo.
          Obras civiles, muebles a medida y fabricaciones especiales, todo bajo un mismo equipo en Santiago.
        </p>
      </div>
    </section>

    {/* Content */}
    <section className="section-padding bg-background">
      <div className="container mx-auto max-w-4xl space-y-12">

        {/* Split: text + founder photo */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 items-center">
          <div className="space-y-8">
            <div>
              <h2 className="font-heading text-2xl font-bold text-foreground mb-4 uppercase flex items-center gap-3">
                <span className="w-8 h-0.5 bg-primary inline-block" aria-hidden="true" /> Nuestra Historia
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                Fundados en 2021 en Santiago, nacimos con el propósito de ser el proveedor que resuelve
                múltiples necesidades bajo un mismo techo. Lo que comenzó como una empresa de ingeniería
                evolucionó hacia un modelo más cercano al cliente: obras de oficina, muebles a medida
                y fabricaciones especiales para empresas que necesitan soluciones concretas, rápidas y sin complicaciones.
              </p>
            </div>
            <div>
              <h2 className="font-heading text-2xl font-bold text-foreground mb-4 uppercase flex items-center gap-3">
                <span className="w-8 h-0.5 bg-primary inline-block" aria-hidden="true" /> Misión
              </h2>
              <p className="text-muted-foreground leading-relaxed">
                Transformar espacios y fabricar soluciones con calidad, transparencia y cumplimiento de plazos.
                Ser el proveedor de confianza que las empresas necesitan para sus proyectos de infraestructura interna.
              </p>
            </div>
          </div>
          <div className="relative">
            <img
              src={IMAGES.jorgeVaras}
              alt="Jorge Varas, Fundador de U&J Ingeniería e Instalaciones Spa, Santiago Chile"
              className="rounded w-full object-cover aspect-square shadow-xl"
              loading="lazy"
            />
            <div className="absolute bottom-4 left-4 right-4 bg-dark/80 backdrop-blur-sm rounded p-4">
              <p className="font-heading font-bold text-primary text-sm uppercase tracking-widest">Jorge Varas</p>
              <p className="text-dark-foreground text-xs mt-0.5">Fundador · U&J Ingeniería</p>
            </div>
          </div>
        </div>

        {/* Values */}
        <div>
          <h2 className="font-heading text-2xl font-bold text-foreground mb-6 uppercase text-center">Nuestros Valores</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {values.map((v, i) => (
              <div key={i} className="p-6 bg-card border-t-4 border-primary border-x border-b border-border rounded">
                <div className="font-heading text-5xl font-bold text-primary/10 mb-3 leading-none" aria-hidden="true">{String(i + 1).padStart(2, "0")}</div>
                <h3 className="font-heading text-lg font-bold text-foreground mb-2 uppercase">{v.title}</h3>
                <p className="text-sm text-muted-foreground leading-relaxed">{v.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* Quote */}
        <blockquote className="bg-navy rounded p-10 text-center">
          <div className="font-heading text-8xl text-primary/20 leading-none mb-4" aria-hidden="true">"</div>
          <p className="font-heading text-xl md:text-2xl text-navy-foreground italic leading-relaxed max-w-2xl mx-auto mb-4">
            Nuestro compromiso es generar valor para nuestros clientes mediante la aplicación eficiente e íntegra de nuestro trabajo.
          </p>
          <div className="w-12 h-0.5 bg-primary mx-auto mb-3" aria-hidden="true" />
          <footer className="text-primary font-heading font-bold text-sm uppercase tracking-widest">
            Jorge Varas · Fundador, U&J Ingeniería
          </footer>
        </blockquote>

        <div className="text-center pt-4">
          <Link to="/cotizar" className="inline-flex items-center gap-2 px-8 py-3.5 bg-primary text-primary-foreground font-heading font-bold rounded hover:opacity-90 transition-opacity">
            Trabajemos juntos <ArrowRight className="h-4 w-4" aria-hidden="true" />
          </Link>
        </div>
      </div>
    </section>
  </Layout>
);

export default AboutPage;
