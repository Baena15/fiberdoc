import {
  BrowserRouter,
  Navigate,
  Outlet,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import AppLayout from "./components/AppLayout";
import LoginPage from "./pages/LoginPage";
import PanelObraPage from "./pages/PanelObraPage";
import SpliceMatrixPage from "./pages/SpliceMatrixPage";

/** Guarda de rutas: sin sesión → /login (preservando el destino). */
function RutaProtegida() {
  const { usuario, cargando } = useAuth();
  const location = useLocation();

  if (cargando) {
    return (
      <p className="min-h-screen flex items-center justify-center text-tinta/60">
        Comprobando sesión…
      </p>
    );
  }
  if (!usuario) {
    const next = encodeURIComponent(location.pathname + location.search);
    return <Navigate to={`/login?next=${next}`} replace />;
  }
  return <Outlet />;
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RutaProtegida />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<PanelObraPage />} />
              <Route path="/elementos/:id" element={<SpliceMatrixPage />} />
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
