/**
 * Tipos TypeScript del contrato de la API REST de FiberDoc (Django + DRF).
 * Ver apps/network/serializers.py en el backend.
 */

/** Usuario autenticado (GET /api/auth/me/). */
export interface Usuario {
  id: number;
  username: string;
  rol: "ADMIN_CONTRATA" | "CAPATAZ" | "FUSIONADOR";
  contrata: string | null;
}

export interface Obra {
  id: number;
  cliente: number;
  perfil_operadora: number;
  codigo: string;
  direccion: string;
  ubicacion: string;
  arquitectura: string;
  estado: string;
  umbrales: Record<string, { ok: number; warn: number }> | null;
  potencia_min_dbm: string | null;
  potencia_max_dbm: string | null;
  requiere_otdr: boolean;
  creado: string;
  modificado: string;
}

export type TipoElemento = "EMPALME" | "CTO" | "REGISTRO" | "ODF" | "CJA_TERMINAL";

export interface ElementoRed {
  id: number;
  obra: number;
  tipo: TipoElemento;
  codigo: string;
  direccion: string;
  ubicacion_tipo: string;
  lat: string | null;
  long: string | null;
  capacidad_puertos: number;
}

/** GET /api/elementos/{id}/resumen/ */
export interface ResumenElemento {
  elemento: number;
  fusiones_activas: number;
  por_estado: Record<string, number>;
  por_nivel: Partial<Record<"OK" | "WARNING" | "FUERA" | "SIN_MEDIDA", number>>;
  conexiones_activas: number;
}

export interface Cable {
  id: number;
  obra: number;
  elemento_a: number;
  elemento_b: number;
  codigo: string;
  tipo_cable: string;
  tipo_fibra: string;
  n_tubos: number;
  fibras_por_tubo: number;
  n_fibras: number;
  longitud_m: string;
}

export type Nivel = "OK" | "WARNING" | "FUERA";

/** Fila sparse de GET /api/elementos/{id}/matriz/ */
export interface MatrizFila {
  fusion_id: number;
  tubo_a: number;
  fibra_a: number;
  tubo_b: number;
  fibra_b: number;
  perdida_db: string | null;
  nivel: Nivel | null;
  estado: string;
}

export interface MatrizResponse {
  elemento: number;
  cable_a: number;
  cable_b: number;
  filas: MatrizFila[];
}
