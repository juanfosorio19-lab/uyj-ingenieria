import Navbar from "./Navbar";
import Footer from "./Footer";
import { useEffect } from "react";

interface LayoutProps {
  children: React.ReactNode;
  title?: string;
  description?: string;
}

// JSON-LD Schema de la empresa
const organizationSchema = {
  "@context": "https://schema.org",
  "@type": "LocalBusiness",
  "name": "U&J Ingeniería e Instalaciones Spa",
  "url": "https://www.uingenieria.com",
  "logo": "https://static.wixstatic.com/media/48a65c_44fe801359974539a58a61023d6762cc~mv2.png",
  "description": "Remodelación de oficinas, muebles a medida y fabricaciones especiales para empresas en Santiago, Chile.",
  "address": {
    "@type": "PostalAddress",
    "streetAddress": "Calle La Finca #914, Interior 115",
    "addressLocality": "Lampa",
    "addressRegion": "Región Metropolitana",
    "addressCountry": "CL"
  },
  "telephone": "+56972800950",
  "email": "info@uingenieria.com",
  "foundingDate": "2021",
  "areaServed": ["Santiago", "Chile"],
  "hasOfferCatalog": {
    "@type": "OfferCatalog",
    "name": "Servicios U&J",
    "itemListElement": [
      { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Obras Civiles y Remodelación de Oficinas" } },
      { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Muebles a Medida y Carpintería" } },
      { "@type": "Offer", "itemOffered": { "@type": "Service", "name": "Maestranza y Fabricaciones Especiales" } },
    ]
  },
  "sameAs": ["https://www.linkedin.com/company/uyj-ingenieria"]
};

const Layout = ({ children, title, description }: LayoutProps) => {
  useEffect(() => {
    if (title) document.title = title;
    if (description) {
      const meta = document.querySelector('meta[name="description"]');
      if (meta) meta.setAttribute("content", description);
    }
  }, [title, description]);

  return (
    <div className="min-h-screen flex flex-col">
      {/* JSON-LD Schema */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />
      <Navbar />
      <main className="flex-1 pt-16" id="main-content">
        {children}
      </main>
      <Footer />
    </div>
  );
};

export default Layout;
