import type { Nivel } from "../api/types";

export type Semaforo = Nivel | "NEUTRO";

/** Peor nivel agregado de un resumen (FUERA > WARNING > OK; sin fusiones → NEUTRO). */
export function semaforoDeResumen(
  porNivel: Partial<Record<Nivel | "SIN_MEDIDA", number>>,
  fusionesActivas: number,
): Semaforo {
  if (fusionesActivas === 0) return "NEUTRO";
  if ((porNivel.FUERA ?? 0) > 0) return "FUERA";
  if ((porNivel.WARNING ?? 0) > 0) return "WARNING";
  return "OK";
}

const ESTILO_PUNTO: Record<Semaforo, string> = {
  OK: "bg-ok",
  WARNING: "bg-warn",
  FUERA: "bg-fuera",
  NEUTRO: "bg-[#b8aea1]",
};

export function PuntoSemaforo({ nivel }: { nivel: Semaforo }) {
  return (
    <span
      aria-label={`Semáforo ${nivel}`}
      className={`inline-block w-3 h-3 rounded-full align-middle ${ESTILO_PUNTO[nivel]}`}
    />
  );
}

const ESTILO_BADGE: Record<Semaforo, string> = {
  OK: "border-ok text-[#4f734f] bg-ok/15",
  WARNING: "border-warn text-[#8a6420] bg-warn/15",
  FUERA: "border-fuera text-[#94453a] bg-fuera/10",
  NEUTRO: "border-[#cfc6ba] text-tinta/60 bg-arena",
};

const TEXTO_BADGE: Record<Semaforo, string> = {
  OK: "Todo OK",
  WARNING: "Con avisos",
  FUERA: "Fuera de umbral",
  NEUTRO: "Sin fusiones",
};

export function BadgeSemaforo({ nivel }: { nivel: Semaforo }) {
  return (
    <span
      className={`inline-block text-[11px] font-semibold rounded-full border px-2.5 py-0.5 whitespace-nowrap ${ESTILO_BADGE[nivel]}`}
    >
      {TEXTO_BADGE[nivel]}
    </span>
  );
}

const ESTILO_CHIP_NIVEL: Record<Nivel, string> = {
  OK: "border-ok text-[#4f734f] bg-ok/15",
  WARNING: "border-warn text-[#8a6420] bg-warn/15",
  FUERA: "border-fuera text-[#94453a] bg-fuera/10",
};

export function ChipNivel({
  nivel,
  cantidad,
}: {
  nivel: Nivel;
  cantidad: number;
}) {
  const texto = nivel === "FUERA" ? "Fuera" : nivel === "WARNING" ? "Avisos" : "OK";
  return (
    <span
      className={`inline-block text-xs font-semibold rounded-full border px-2.5 py-1 whitespace-nowrap ${ESTILO_CHIP_NIVEL[nivel]}`}
    >
      {texto}: {cantidad}
    </span>
  );
}
