/** Colores y utilidades de tubos/fibras (código DIN VDE 0888). */

const COLORES_FIBRA = [
  { nombre: "azul", clase: "fib-azul" },
  { nombre: "naranja", clase: "fib-naranja" },
  { nombre: "verde", clase: "fib-verde" },
  { nombre: "marrón", clase: "fib-marron" },
  { nombre: "gris", clase: "fib-gris" },
  { nombre: "blanco", clase: "fib-blanco" },
  { nombre: "rojo", clase: "fib-rojo" },
  { nombre: "negro", clase: "fib-negro" },
  { nombre: "amarillo", clase: "fib-amarillo" },
  { nombre: "violeta", clase: "fib-violeta" },
  { nombre: "rosa", clase: "fib-rosa" },
  { nombre: "turquesa", clase: "fib-turquesa" },
] as const;

/** Color (1-based) de un tubo o fibra dentro de su grupo. */
export function colorFibra(indice: number) {
  return COLORES_FIBRA[(indice - 1) % COLORES_FIBRA.length];
}

export function etiquetaTipoElemento(tipo: string): string {
  const etiquetas: Record<string, string> = {
    EMPALME: "Empalme",
    CTO: "Caja CTO",
    REGISTRO: "Registro",
    ODF: "ODF",
    CJA_TERMINAL: "Caja terminal",
  };
  return etiquetas[tipo] ?? tipo;
}

export function etiquetaEstado(estado: string): string {
  const etiquetas: Record<string, string> = {
    EJECUTADA: "Ejecutada",
    MEDIDA: "Medida",
    VALIDADA: "Validada",
    CERTIFICADA: "Certificada",
  };
  return etiquetas[estado] ?? estado;
}
