import { useState, type FormEvent } from "react";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";

/** Pantalla de acceso: formulario grande, mobile-first, error claro si 401. */
export default function LoginPage() {
  const { usuario, cargando, login } = useAuth();
  const navigate = useNavigate();
  const [params] = useSearchParams();
  const destino = params.get("next") || "/";

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  if (!cargando && usuario) {
    // Ya hay sesión activa: directo al panel.
    return <Navigate to={destino} replace />;
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      await login(username.trim(), password);
      navigate(destino, { replace: true });
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 401
          ? "Usuario o contraseña incorrectos. Revísalo e inténtalo de nuevo."
          : "No se pudo conectar con el servidor. Inténtalo en unos segundos.",
      );
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="min-h-screen flex items-start sm:items-center justify-center px-4 pt-10 sm:pt-0">
      <div className="w-full max-w-sm bg-white border border-linea rounded-xl shadow-sm p-6 sm:p-8">
        <div className="text-center mb-6">
          <div className="w-14 h-14 rounded-xl bg-acento text-white text-2xl font-bold flex items-center justify-center mx-auto mb-3">
            E
          </div>
          <h1 className="text-2xl font-bold">FiberDoc</h1>
          <p className="text-sm text-tinta/60 mt-1">
            Trazabilidad de empalmes para contratas de fibra óptica
          </p>
        </div>

        <form onSubmit={onSubmit} noValidate>
          <label
            htmlFor="usuario"
            className="block text-sm font-semibold text-tinta/70 mb-1.5"
          >
            Usuario
          </label>
          <input
            id="usuario"
            type="text"
            autoComplete="username"
            autoFocus
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="p. ej. fusionador"
            className="w-full text-base rounded-lg border border-[#cfc6ba] bg-[#fdfcfa] px-4 py-3.5 mb-4 focus:outline-none focus:ring-2 focus:ring-acento/40 focus:border-acento"
          />

          <label
            htmlFor="password"
            className="block text-sm font-semibold text-tinta/70 mb-1.5"
          >
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
            className="w-full text-base rounded-lg border border-[#cfc6ba] bg-[#fdfcfa] px-4 py-3.5 mb-4 focus:outline-none focus:ring-2 focus:ring-acento/40 focus:border-acento"
          />

          {error && (
            <p
              role="alert"
              className="text-sm font-medium text-[#94453a] bg-fuera/10 border border-fuera rounded-lg px-3 py-2.5 mb-4"
            >
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={enviando || !username || !password}
            className="w-full rounded-lg bg-acento text-white font-semibold text-base px-4 py-4 hover:bg-acento-oscuro active:bg-acento-oscuro disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {enviando ? "Entrando…" : "Entrar →"}
          </button>
        </form>

        <p className="text-xs text-tinta/50 text-center mt-5">
          ¿Sin cuenta? Contacta con tu jefe de obra para recibir invitación.
        </p>
      </div>
    </div>
  );
}
