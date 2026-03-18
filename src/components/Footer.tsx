import { Link } from "react-router-dom";
import { Mail, Phone, MapPin, Linkedin } from "lucide-react";

const Footer = () => (
  <footer className="bg-dark text-dark-foreground border-t-4 border-primary">
    <div className="container mx-auto px-4 py-12">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">

        {/* Brand */}
        <div>
          <h3 className="font-heading text-xl font-bold text-primary mb-3">U&J Soluciones</h3>
          <p className="text-sm text-muted-foreground leading-relaxed mb-4">
            Obras civiles, muebles a medida y fabricaciones especiales para empresas en Santiago, Chile.
          </p>
          <a
            href="https://www.linkedin.com/company/uyj-ingenieria"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-primary transition-colors"
          >
            <Linkedin className="h-4 w-4 text-primary" />
            LinkedIn
          </a>
        </div>

        {/* Services */}
        <div>
          <h4 className="font-heading font-bold mb-3 text-primary text-sm uppercase tracking-widest">Servicios</h4>
          <ul className="space-y-2 text-sm">
            <li>
              <Link to="/servicios/obras-civiles" className="text-muted-foreground hover:text-primary transition-colors">
                Obras Civiles y Remodelación
              </Link>
            </li>
            <li>
              <Link to="/servicios/muebles-medida" className="text-muted-foreground hover:text-primary transition-colors">
                Muebles a Medida
              </Link>
            </li>
            <li>
              <Link to="/servicios/maestranza" className="text-muted-foreground hover:text-primary transition-colors">
                Maestranza y Fabricaciones
              </Link>
            </li>
          </ul>
        </div>

        {/* Navigation */}
        <div>
          <h4 className="font-heading font-bold mb-3 text-primary text-sm uppercase tracking-widest">Empresa</h4>
          <ul className="space-y-2 text-sm">
            <li><Link to="/" className="text-muted-foreground hover:text-primary transition-colors">Inicio</Link></li>
            <li><Link to="/nosotros" className="text-muted-foreground hover:text-primary transition-colors">Nosotros</Link></li>
            <li><Link to="/cotizar" className="text-muted-foreground hover:text-primary transition-colors">Solicitar Cotización</Link></li>
          </ul>
        </div>

        {/* Contact */}
        <div>
          <h4 className="font-heading font-bold mb-3 text-primary text-sm uppercase tracking-widest">Contacto</h4>
          <ul className="space-y-2.5 text-sm">
            <li className="flex items-start gap-2">
              <MapPin className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <span className="text-muted-foreground">Calle La Finca #914, Interior 115<br />Lampa, Santiago, Chile</span>
            </li>
            <li className="flex items-center gap-2">
              <Phone className="h-4 w-4 text-primary shrink-0" />
              <a href="tel:+56972800950" className="text-muted-foreground hover:text-primary transition-colors">+56 9 7280 0950</a>
            </li>
            <li className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-primary shrink-0" />
              <a href="mailto:info@uingenieria.com" className="text-muted-foreground hover:text-primary transition-colors">info@uingenieria.com</a>
            </li>
          </ul>
        </div>
      </div>

      <div className="border-t border-navy mt-10 pt-6 text-center text-xs text-muted-foreground">
        © {new Date().getFullYear()} U&J Ingeniería e Instalaciones Spa · Santiago, Chile · Todos los derechos reservados.
      </div>
    </div>
  </footer>
);

export default Footer;
