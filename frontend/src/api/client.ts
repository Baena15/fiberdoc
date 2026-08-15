/**
 * Cliente fetch mínimo para la API de FiberDoc.
 *
 * - Base relativa `/api` (en dev la resuelve el proxy de Vite → :8000).
 * - `credentials: "same-origin"` para que viajen las cookies de sesión.
 * - Los POST llevan la cabecera `X-CSRFToken` leída de la cookie
 *   `csrftoken` que siembra el login (ensure_csrf_cookie).
 * - Un 401 en endpoints de datos redirige a /login (sesión caducada);
 *   las llamadas de auth (/auth/*) devuelven el error sin redirigir.
 */
import type {
  Cable,
  ElementoRed,
  MatrizResponse,
  Obra,
  ResumenElemento,
  Usuario,
} from "./types";

const BASE = "/api";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function getCookie(nombre: string): string | null {
  const encontrada = document.cookie
    .split("; ")
    .find((c) => c.startsWith(`${nombre}=`));
  return encontrada ? decodeURIComponent(encontrada.split("=")[1]) : null;
}

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const metodo = (options.method ?? "GET").toUpperCase();
  const headers: Record<string, string> = {
    Accept: "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (metodo !== "GET" && metodo !== "HEAD") {
    headers["Content-Type"] = "application/json";
    const csrf = getCookie("csrftoken");
    if (csrf) headers["X-CSRFToken"] = csrf;
  }

  const resp = await fetch(`${BASE}${path}`, {
    credentials: "same-origin",
    ...options,
    headers,
  });

  if (resp.status === 401 && !path.startsWith("/auth/")) {
    // Sesión caducada: volver al login preservando la ruta destino.
    const destino = encodeURIComponent(
      window.location.pathname + window.location.search,
    );
    window.location.assign(`/login?next=${destino}`);
    throw new ApiError(401, "Sesión caducada.");
  }
  if (!resp.ok) {
    let detalle = `Error ${resp.status}`;
    try {
      const cuerpo = await resp.json();
      detalle = cuerpo.detail ?? detalle;
    } catch {
      /* respuesta sin cuerpo JSON */
    }
    throw new ApiError(resp.status, detalle);
  }
  if (resp.status === 204) return undefined as T;
  return (await resp.json()) as T;
}

// --- Auth (sesión Django) ---
export const authApi = {
  login: (username: string, password: string) =>
    request<Usuario>("/auth/login/", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<void>("/auth/logout/", { method: "POST" }),
  me: () => request<Usuario>("/auth/me/"),
};

// --- Datos de red (solo GET: el frontend de esta fase es de consulta) ---
export const api = {
  obras: () => request<Obra[]>("/obras/"),
  elementos: () => request<ElementoRed[]>("/elementos/"),
  elemento: (id: number) => request<ElementoRed>(`/elementos/${id}/`),
  resumen: (elementoId: number) =>
    request<ResumenElemento>(`/elementos/${elementoId}/resumen/`),
  matriz: (elementoId: number, cableA: number, cableB: number) =>
    request<MatrizResponse>(
      `/elementos/${elementoId}/matriz/?cable_a=${cableA}&cable_b=${cableB}`,
    ),
  cables: () => request<Cable[]>("/cables/"),
};
