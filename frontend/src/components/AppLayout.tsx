import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const ETIQUETA_ROL: Record<string, string> = {
  ADMIN_CONTRATA: "Administrador",
  CAPATAZ: "Capataz",
  FUSIONADOR: "Fusionador",
};

/** Marco de la app autenticada: cabecera con marca, usuario y "Salir". */
export default function AppLayout() {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();

  const salir = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <div className="min-h-screen flex flex-col">
      <header className="sticky top-0 z-20 bg-arena border-b border-linea">
        <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-3">
          <Link to="/" className="flex items-center gap-2 shrink-0">
            <span className="w-8 h-8 rounded-lg bg-acento text-white flex items-center justify-center font-bold">
              E
            </span>
            <span className="font-bold text-lg">FiberDoc</span>
          </Link>
          <div className="flex-1" />
          {usuario && (
            <div className="text-right leading-tight">
              <p className="text-sm font-semibold">{usuario.username}</p>
              <p className="text-xs text-tinta/60">
                {ETIQUETA_ROL[usuario.rol] ?? usuario.rol}
                {usuario.contrata ? ` · ${usuario.contrata}` : ""}
              </p>
            </div>
          )}
          <button
            type="button"
            onClick={salir}
            className="ml-1 rounded-md border border-acento text-acento font-semibold text-sm px-4 py-2.5 hover:bg-acento/10 active:bg-acento/20"
          >
            Salir
          </button>
        </div>
      </header>
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 py-5">
        <Outlet />
      </main>
      <footer className="text-center text-[11px] uppercase tracking-wider text-tinta/40 pb-4">
        FiberDoc TFM · Trazabilidad de empalmes FTTH
      </footer>
    </div>
  );
}
