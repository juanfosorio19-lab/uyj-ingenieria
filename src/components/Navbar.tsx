import { useState } from "react";
import { Link } from "react-router-dom";
import { Menu, X, ChevronDown } from "lucide-react";
import logo from "@/assets/logo.png";

const navCategories = [
  {
    label: "Ingeniería y Fabricación",
    items: [
      { label: "Fibra de Vidrio (FRP)",       href: "/servicios/fibra-de-vidrio" },
      { label: "Soldadura de Termoplásticos", href: "/servicios/soldadura-termoplasticos" },
      { label: "Tableros Eléctricos",         href: "/servicios/tableros-electricos" },
      { label: "Maestranza y Fabricaciones",  href: "/servicios/maestranza" },
    ],
  },
  {
    label: "Obras y Construcción",
    items: [
      { label: "Obras Civiles y Remodelación", href: "/servicios/obras-civiles" },
    ],
  },
  {
    label: "Muebles y Espacios",
    items: [
      { label: "Muebles a Medida", href: "/servicios/muebles-medida" },
    ],
  },
];

const Navbar = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-dark/95 backdrop-blur-sm border-b border-primary/30">
      <div className="container mx-auto flex items-center justify-between h-16 px-4">
        <Link to="/" className="flex items-center gap-2">
          <img src={logo} alt="U&J Ingeniería e Instalaciones Spa" className="h-10 w-auto" />
          <div className="flex flex-col leading-none">
            <span className="font-heading text-base font-bold text-primary">U&J</span>
            <span className="font-heading text-xs text-dark-foreground/70 tracking-widest uppercase">Ingeniería</span>
          </div>
        </Link>

        {/* Desktop */}
        <div className="hidden lg:flex items-center gap-1">
          <Link to="/" className="px-3 py-2 text-sm font-medium text-dark-foreground hover:text-primary transition-colors">Inicio</Link>
          {navCategories.map((cat) => (
            <div key={cat.label} className="relative" onMouseEnter={() => setOpenDropdown(cat.label)} onMouseLeave={() => setOpenDropdown(null)}>
              <button className="flex items-center gap-1 px-3 py-2 text-sm font-medium text-dark-foreground hover:text-primary transition-colors">
                {cat.label} <ChevronDown className="h-3 w-3" />
              </button>
              {openDropdown === cat.label && (
                <div className="absolute top-full left-0 bg-dark border border-navy rounded shadow-xl min-w-[240px] py-1 animate-fade-in">
                  {cat.items.map((item) => (
                    <Link key={item.href} to={item.href} className="block px-4 py-2.5 text-sm text-dark-foreground hover:bg-navy hover:text-primary transition-colors border-l-2 border-transparent hover:border-primary">
                      {item.label}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
          <Link to="/nosotros" className="px-3 py-2 text-sm font-medium text-dark-foreground hover:text-primary transition-colors">Nosotros</Link>
          <Link to="/cotizar" className="ml-4 px-5 py-2 bg-primary text-primary-foreground font-heading font-bold text-sm rounded hover:opacity-90 transition-opacity">
            Solicitar Cotización
          </Link>
        </div>

        {/* Mobile */}
        <button className="lg:hidden text-dark-foreground" onClick={() => setMobileOpen(!mobileOpen)} aria-label="Menú">
          {mobileOpen ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="lg:hidden bg-dark border-t border-navy animate-fade-in">
          <div className="px-4 py-4 space-y-1">
            <Link to="/" className="block py-2 text-dark-foreground hover:text-primary" onClick={() => setMobileOpen(false)}>Inicio</Link>
            {navCategories.map((cat) => (
              <div key={cat.label}>
                <button className="flex items-center justify-between w-full py-2 text-dark-foreground font-medium" onClick={() => setOpenDropdown(openDropdown === cat.label ? null : cat.label)}>
                  {cat.label} <ChevronDown className={`h-4 w-4 transition-transform ${openDropdown === cat.label ? "rotate-180" : ""}`} />
                </button>
                {openDropdown === cat.label && (
                  <div className="pl-4 space-y-1">
                    {cat.items.map((item) => (
                      <Link key={item.href} to={item.href} className="block py-2 text-sm text-muted-foreground hover:text-primary" onClick={() => setMobileOpen(false)}>{item.label}</Link>
                    ))}
                  </div>
                )}
              </div>
            ))}
            <Link to="/nosotros" className="block py-2 text-dark-foreground hover:text-primary" onClick={() => setMobileOpen(false)}>Nosotros</Link>
            <Link to="/cotizar" className="block mt-3 text-center px-5 py-2.5 bg-primary text-primary-foreground font-heading font-bold rounded" onClick={() => setMobileOpen(false)}>
              Solicitar Cotización
            </Link>
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
