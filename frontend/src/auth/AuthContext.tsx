import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { authApi, ApiError } from "../api/client";
import type { Usuario } from "../api/types";

interface AuthContextValue {
  usuario: Usuario | null;
  /** true mientras se comprueba la sesión al arrancar la app. */
  cargando: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);

  // Al arrancar: ¿hay sesión activa? (401 → no la hay, es normal)
  useEffect(() => {
    authApi
      .me()
      .then(setUsuario)
      .catch((err) => {
        if (!(err instanceof ApiError && err.status === 401)) {
          console.error("Error comprobando la sesión:", err);
        }
      })
      .finally(() => setCargando(false));
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const u = await authApi.login(username, password);
    setUsuario(u);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      setUsuario(null);
    }
  }, []);

  const value = useMemo(
    () => ({ usuario, cargando, login, logout }),
    [usuario, cargando, login, logout],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de <AuthProvider>");
  return ctx;
}
