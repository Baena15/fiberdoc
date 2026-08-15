import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import type {
  Cable,
  ElementoRed,
  MatrizFila,
  MatrizResponse,
  Nivel,
  ResumenElemento,
} from "../api/types";
import { ChipNivel } from "../components/Semaforo";
import { colorFibra, etiquetaEstado, etiquetaTipoElemento } from "../utils/fibras";

interface Posicion {
  tubo: number;
  fibra: number;
}

/** Posiciones (tubo, fibra) de un cable a partir de su geometría. */
function posicionesDe(cable: Cable): Posicion[] {
  const posiciones: Posicion[] = [];
  for (let tubo = 1; tubo <= cable.n_tubos; tubo++) {
    for (let fibra = 1; fibra <= cable.fibras_por_tubo; fibra++) {
      posiciones.push({ tubo, fibra });
    }
  }
  return posiciones;
}

function clave(t: number, f: number): string {
  return `${t}-${f}`;
}

/** SpliceMatrix: matriz de fusiones entre dos cables de un elemento. */
export default function SpliceMatrixPage() {
  const { id } = useParams<{ id: string }>();
  const elementoId = Number(id);

  const [elemento, setElemento] = useState<ElementoRed | null>(null);
  const [resumen, setResumen] = useState<ResumenElemento | null>(null);
  const [cables, setCables] = useState<Cable[] | null>(null);
  const [errorCarga, setErrorCarga] = useState<string | null>(null);

  const [cableAId, setCableAId] = useState<number | null>(null);
  const [cableBId, setCableBId] = useState<number | null>(null);

  const [matriz, setMatriz] = useState<MatrizResponse | null>(null);
  const [cargandoMatriz, setCargandoMatriz] = useState(false);
  const [errorMatriz, setErrorMatriz] = useState<string | null>(null);

  const [seleccion, setSeleccion] = useState<MatrizFila | null>(null);

  // Carga inicial: elemento, su resumen y los cables que lo tocan.
  useEffect(() => {
    if (!Number.isFinite(elementoId)) {
      setErrorCarga("Elemento no válido.");
      return;
    }
    let cancelado = false;
    Promise.all([api.elemento(elementoId), api.resumen(elementoId), api.cables()])
      .then(([el, res, todosCables]) => {
        if (cancelado) return;
        setElemento(el);
        setResumen(res);
        const delElemento = todosCables.filter(
          (c) => c.elemento_a === el.id || c.elemento_b === el.id,
        );
        setCables(delElemento);
      })
      .catch(() => {
        if (!cancelado) setErrorCarga("No se pudo cargar el elemento de red.");
      });
    return () => {
      cancelado = true;
    };
  }, [elementoId]);

  const cableA = cables?.find((c) => c.id === cableAId) ?? null;
  const cableB = cables?.find((c) => c.id === cableBId) ?? null;

  // Matriz: solo cuando hay dos cables distintos elegidos.
  useEffect(() => {
    setSeleccion(null);
    if (!cableAId || !cableBId || cableAId === cableBId) {
      setMatriz(null);
      setErrorMatriz(null);
      return;
    }
    let cancelado = false;
    setCargandoMatriz(true);
    setErrorMatriz(null);
    api
      .matriz(elementoId, cableAId, cableBId)
      .then((m) => {
        if (!cancelado) setMatriz(m);
      })
      .catch(() => {
        if (!cancelado) setErrorMatriz("No se pudo cargar la matriz de fusiones.");
      })
      .finally(() => {
        if (!cancelado) setCargandoMatriz(false);
      });
    return () => {
      cancelado = true;
    };
  }, [elementoId, cableAId, cableBId]);

  // Índice: (tuboA, fibraA) → (tuboB, fibraB) → fila
  const indice = useMemo(() => {
    const mapa = new Map<string, Map<string, MatrizFila>>();
    for (const fila of matriz?.filas ?? []) {
      const origen = clave(fila.tubo_a, fila.fibra_a);
      const destino = clave(fila.tubo_b, fila.fibra_b);
      if (!mapa.has(origen)) mapa.set(origen, new Map());
      mapa.get(origen)!.set(destino, fila);
    }
    return mapa;
  }, [matriz]);

  if (errorCarga) {
    return (
      <div className="space-y-4">
        <VolverAlPanel />
        <p role="alert" className="bg-fuera/10 border border-fuera text-[#94453a] rounded-lg px-4 py-3 text-sm font-medium">
          {errorCarga}
        </p>
      </div>
    );
  }
  if (!elemento || !cables) {
    return <p className="text-tinta/60 py-10 text-center">Cargando elemento…</p>;
  }

  const intercambiar = () => {
    setCableAId(cableBId);
    setCableBId(cableAId);
  };

  return (
    <div className="space-y-4">
      <VolverAlPanel />

      {/* Cabecera: elemento + chips de resumen */}
      <section className="bg-white border border-linea rounded-xl p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <div>
            <h2 className="text-lg font-bold font-mono">{elemento.codigo}</h2>
            <p className="text-xs text-tinta/60">
              {etiquetaTipoElemento(elemento.tipo)}
              {elemento.direccion ? ` · ${elemento.direccion}` : ""}
            </p>
          </div>
          <div className="flex-1" />
          {resumen && (
            <div className="flex gap-2 flex-wrap">
              <ChipNivel nivel="OK" cantidad={resumen.por_nivel.OK ?? 0} />
              <ChipNivel nivel="WARNING" cantidad={resumen.por_nivel.WARNING ?? 0} />
              <ChipNivel nivel="FUERA" cantidad={resumen.por_nivel.FUERA ?? 0} />
              <span className="inline-block text-xs font-semibold rounded-full border border-[#cfc6ba] text-tinta/60 bg-arena px-2.5 py-1">
                Total: {resumen.fusiones_activas}
              </span>
            </div>
          )}
        </div>
      </section>

      {/* Selectores de cables */}
      <section className="bg-white border border-linea rounded-xl p-4 shadow-sm">
        <div className="flex flex-wrap items-end gap-3">
          <SelectorCable
            id="cable-a"
            etiqueta="Cable A (origen)"
            cables={cables}
            valor={cableAId}
            onChange={setCableAId}
          />
          <button
            type="button"
            onClick={intercambiar}
            disabled={!cableAId && !cableBId}
            title="Intercambiar cables A/B"
            aria-label="Intercambiar cables A y B"
            className="h-12 w-12 rounded-lg border border-linea bg-arena text-acento text-xl font-bold hover:bg-linea disabled:opacity-40"
          >
            ⇄
          </button>
          <SelectorCable
            id="cable-b"
            etiqueta="Cable B (destino)"
            cables={cables}
            valor={cableBId}
            onChange={setCableBId}
          />
          {matriz && cableA && cableB && (
            <div className="ml-auto rounded-lg border border-acento bg-acento/10 font-bold px-4 py-3 whitespace-nowrap">
              {matriz.filas.length} fusiones
            </div>
          )}
        </div>
        {cables.length === 0 && (
          <p className="text-sm text-tinta/60 mt-3">
            Este elemento no tiene cables asociados.
          </p>
        )}
        {cableAId && cableBId && cableAId === cableBId && (
          <p className="text-sm text-[#8a6420] mt-3">
            Elige dos cables distintos para ver sus fusiones.
          </p>
        )}
      </section>

      {/* Leyenda */}
      <div className="flex gap-x-5 gap-y-1 flex-wrap text-xs text-tinta/70">
        <span>
          <span className="inline-block w-3 h-3 rounded-full bg-ok align-middle mr-1.5" />
          OK — dentro de umbral
        </span>
        <span>
          <span className="inline-block w-3 h-3 rounded-full bg-warn align-middle mr-1.5" />
          Aviso — cerca del límite
        </span>
        <span>
          <span className="inline-block w-3 h-3 rounded-full bg-fuera align-middle mr-1.5" />
          Fuera de umbral — revisar fusión
        </span>
        <span>
          <span className="inline-block w-3 h-3 rounded-full bg-[#d8d1c6] align-middle mr-1.5" />
          Sin fusión / sin medida
        </span>
      </div>

      {/* Matriz */}
      <section className="bg-white border border-linea rounded-xl p-3 shadow-sm">
        {!cableAId || !cableBId ? (
          <EstadoVacio texto="Selecciona dos cables para ver la matriz de fusiones." />
        ) : cableAId === cableBId ? null : cargandoMatriz ? (
          <EstadoVacio texto="Cargando matriz…" />
        ) : errorMatriz ? (
          <p role="alert" className="text-sm font-medium text-[#94453a] p-4">
            {errorMatriz}
          </p>
        ) : matriz && cableA && cableB ? (
          matriz.filas.length === 0 ? (
            <EstadoVacio texto="Sin fusiones entre estos cables." />
          ) : (
            <MatrizFusiones
              cableA={cableA}
              cableB={cableB}
              indice={indice}
              onSeleccion={setSeleccion}
            />
          )
        ) : null}
      </section>

      {matriz && matriz.filas.length > 0 && (
        <p className="text-xs text-tinta/50 px-1">
          Filas: {cableA?.codigo} (tubo/fibra) · Columnas: {cableB?.codigo}.
          Toca una celda coloreada para ver el detalle de la fusión. En móvil,
          desliza horizontalmente.
        </p>
      )}

      {/* Modal de detalle de fusión */}
      {seleccion && cableA && cableB && (
        <DetalleFusion
          fila={seleccion}
          cableA={cableA}
          cableB={cableB}
          onCerrar={() => setSeleccion(null)}
        />
      )}
    </div>
  );
}

function VolverAlPanel() {
  return (
    <Link to="/" className="inline-block text-sm font-semibold text-acento hover:underline">
      ← Volver al panel de obra
    </Link>
  );
}

function EstadoVacio({ texto }: { texto: string }) {
  return <p className="text-tinta/60 text-center py-10 text-sm">{texto}</p>;
}

function SelectorCable({
  id,
  etiqueta,
  cables,
  valor,
  onChange,
}: {
  id: string;
  etiqueta: string;
  cables: Cable[];
  valor: number | null;
  onChange: (id: number | null) => void;
}) {
  return (
    <div className="flex-1 min-w-44">
      <label htmlFor={id} className="block text-xs font-semibold text-tinta/60 mb-1">
        {etiqueta}
      </label>
      <select
        id={id}
        value={valor ?? ""}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : null)}
        className="w-full text-sm font-bold rounded-lg border border-[#cfc6ba] bg-white px-3 py-3 focus:outline-none focus:ring-2 focus:ring-acento/40 focus:border-acento"
      >
        <option value="">— elegir cable —</option>
        {cables.map((c) => (
          <option key={c.id} value={c.id}>
            {c.codigo} ({c.n_fibras}F)
          </option>
        ))}
      </select>
    </div>
  );
}

const ESTILO_CELDA: Record<Nivel, string> = {
  OK: "bg-ok/70 hover:bg-ok",
  WARNING: "bg-warn/70 hover:bg-warn",
  FUERA: "bg-fuera/70 hover:bg-fuera",
};

function MatrizFusiones({
  cableA,
  cableB,
  indice,
  onSeleccion,
}: {
  cableA: Cable;
  cableB: Cable;
  indice: Map<string, Map<string, MatrizFila>>;
  onSeleccion: (fila: MatrizFila) => void;
}) {
  const filasA = posicionesDe(cableA);
  const columnasB = posicionesDe(cableB);
  const tubosB = Array.from({ length: cableB.n_tubos }, (_, i) => i + 1);

  return (
    <div className="overflow-x-auto">
      <table className="border-collapse">
        <thead>
          <tr>
            <th
              rowSpan={2}
              className="sticky left-0 bg-white text-left text-[10px] uppercase tracking-wide text-tinta/50 pr-2 align-bottom pb-1"
            >
              {cableA.codigo} ↓ · {cableB.codigo} →
            </th>
            {tubosB.map((tubo) => (
              <th
                key={tubo}
                colSpan={cableB.fibras_por_tubo}
                className="px-0.5 pt-1 pb-0.5 border-b border-linea"
              >
                <span
                  className={`block rounded text-[9px] font-bold text-white py-0.5 ${colorFibra(tubo).clase}`}
                >
                  T{tubo}
                </span>
              </th>
            ))}
          </tr>
          <tr>
            {columnasB.map((pos) => (
              <th
                key={clave(pos.tubo, pos.fibra)}
                className="text-[9px] font-mono font-normal text-tinta/50 pb-1"
              >
                {pos.fibra}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filasA.map((posA) => {
            const esPrimeraDelTubo = posA.fibra === 1;
            const colorTuboA = colorFibra(posA.tubo);
            return (
              <tr key={clave(posA.tubo, posA.fibra)}>
                <th
                  className={`sticky left-0 bg-white text-left font-mono text-[10px] pr-2 py-0 whitespace-nowrap ${
                    esPrimeraDelTubo ? "pt-1.5" : ""
                  }`}
                >
                  <span
                    className={`inline-block rounded text-white px-1 py-px mr-1 ${colorTuboA.clase}`}
                  >
                    T{posA.tubo}
                  </span>
                  {posA.fibra}
                </th>
                {columnasB.map((posB) => {
                  const fila = indice
                    .get(clave(posA.tubo, posA.fibra))
                    ?.get(clave(posB.tubo, posB.fibra));
                  return (
                    <td key={clave(posB.tubo, posB.fibra)} className="p-px">
                      {fila ? (
                        <button
                          type="button"
                          onClick={() => onSeleccion(fila)}
                          title={`Fusión ${posA.tubo}/${posA.fibra} → ${posB.tubo}/${posB.fibra}${
                            fila.perdida_db != null ? ` · ${fila.perdida_db} dB` : ""
                          }`}
                          aria-label={`Fusión tubo ${posA.tubo} fibra ${posA.fibra} a tubo ${posB.tubo} fibra ${posB.fibra}, nivel ${fila.nivel ?? "sin medida"}`}
                          className={`w-6 h-6 rounded-sm ${
                            fila.nivel ? ESTILO_CELDA[fila.nivel] : "bg-[#d8d1c6] hover:bg-[#c4bab0]"
                          }`}
                        />
                      ) : (
                        <span className="block w-6 h-6 rounded-sm bg-arena/70" />
                      )}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

const ESTILO_BADGE_NIVEL: Record<Nivel, string> = {
  OK: "border-ok text-[#4f734f] bg-ok/15",
  WARNING: "border-warn text-[#8a6420] bg-warn/15",
  FUERA: "border-fuera text-[#94453a] bg-fuera/10",
};

function DetalleFusion({
  fila,
  cableA,
  cableB,
  onCerrar,
}: {
  fila: MatrizFila;
  cableA: Cable;
  cableB: Cable;
  onCerrar: () => void;
}) {
  const perdida =
    fila.perdida_db != null
      ? `${Number(fila.perdida_db).toFixed(3).replace(".", ",")} dB`
      : "Sin medida";
  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Detalle de la fusión"
      className="fixed inset-0 z-30 bg-tinta/40 flex items-end sm:items-center justify-center p-3"
      onClick={onCerrar}
    >
      <div
        className="w-full max-w-sm bg-white rounded-xl border border-linea shadow-lg p-5"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="font-bold text-base mb-3">Detalle de la fusión</h3>

        <div className="flex items-center gap-2 font-mono text-sm mb-4">
          <ChipPosicion cable={cableA} tubo={fila.tubo_a} fibra={fila.fibra_a} />
          <span className="text-acento font-bold">→</span>
          <ChipPosicion cable={cableB} tubo={fila.tubo_b} fibra={fila.fibra_b} />
        </div>

        <dl className="text-sm space-y-2">
          <div className="flex justify-between">
            <dt className="text-tinta/60">Pérdida</dt>
            <dd className="font-mono font-bold">{perdida}</dd>
          </div>
          <div className="flex justify-between items-center">
            <dt className="text-tinta/60">Nivel</dt>
            <dd>
              {fila.nivel ? (
                <span
                  className={`text-[11px] font-semibold rounded-full border px-2.5 py-0.5 ${ESTILO_BADGE_NIVEL[fila.nivel]}`}
                >
                  {fila.nivel === "FUERA" ? "Fuera de umbral" : fila.nivel}
                </span>
              ) : (
                <span className="text-[11px] font-semibold rounded-full border border-[#cfc6ba] text-tinta/60 bg-arena px-2.5 py-0.5">
                  Sin medida
                </span>
              )}
            </dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-tinta/60">Estado</dt>
            <dd className="font-semibold">{etiquetaEstado(fila.estado)}</dd>
          </div>
        </dl>

        <button
          type="button"
          onClick={onCerrar}
          className="mt-5 w-full rounded-lg bg-acento text-white font-semibold px-4 py-3.5 hover:bg-acento-oscuro"
        >
          Cerrar
        </button>
      </div>
    </div>
  );
}

function ChipPosicion({
  cable,
  tubo,
  fibra,
}: {
  cable: Cable;
  tubo: number;
  fibra: number;
}) {
  const colorTubo = colorFibra(tubo);
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className={`rounded px-1.5 py-0.5 text-white text-xs font-bold ${colorTubo.clase}`}>
        T{tubo}
      </span>
      <span className="font-semibold">F{fibra}</span>
      <span className="text-tinta/40 text-xs">({cable.codigo})</span>
    </span>
  );
}
