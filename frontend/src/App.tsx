import { EssentialDrugs } from './components/EssentialDrugs';
import logo from './assets/logo.png';
import { Pill } from 'lucide-react';

function App() {
  return (
    <div className="min-h-screen bg-[#F8FAFC] font-sans text-gray-900">
      <header className="bg-white border-b border-gray-200 py-3 px-6 sticky top-0 z-50 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div className="flex items-center gap-3">
            <img src={logo} alt="Dose Mind" className="h-10 w-auto object-contain" />
            <span className="font-bold text-xl text-[#005CA9] tracking-tight hidden md:inline">Dose Mind</span>
          </div>

          <nav className="flex items-center gap-1 bg-gray-100 p-1 rounded-xl">
            <div
              className="flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-bold bg-white text-[#005CA9] shadow-sm"
            >
              <Pill className="h-4 w-4" />
              Medicamentos esenciales
            </div>
          </nav>
        </div>
      </header>

      <main className="container mx-auto py-8">
        <EssentialDrugs />
      </main>

      <footer className="bg-white border-t border-gray-200 mt-auto py-8 text-center text-gray-400 text-sm">
        <div className="container mx-auto px-4">
          <p className="font-medium">© 2026 Dose Mind. Todos los derechos reservados.</p>
          <p className="text-xs mt-1">Plataforma avanzada de asistencia farmacéutica e inteligente.</p>
        </div>
      </footer>
    </div >
  );
}

export default App;
