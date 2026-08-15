import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import type { ElementoRed, Obra, ResumenElemento } from "../api/types";
import { BadgeSemaforo, semaforoDeResumen } from "../components/Semaforo";
import { etiquetaTipoElemento } from "../utils/fibras";

interface ElementoConResumen {
  elemento: ElementoRed;
  resumen: ResumenElemento | null;
}

/** Panel de obra: selector de obra + tarjetas de elementos con semáforo. */
export default function PanelObraPage() {
  const [obras, setObras] = useState<Obra[] | null>(null);
  const [obraId, setObraId] = useState<number | null>(null);
  const [elementos, setElementos] = useState<ElementoConResumen[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Carga inicial: obras y elementos (se filtran por contrata en el backend).
  useEffect(() => {
    let cancelado = false;
    Promise.all([api.obras(), api.elementos()])
      .then(async ([listaObras, listaElementos]) => {
        if (cancelado) return;
        setObras(listaObras);
        const primera = listaObras[0]?.id ?? null;
        setObraId(primera);
        // Resumen por elemento (volumen pequeño por obra: sin problema de N+1 aquí).
        const conResumen = await Promise.all(
          listaElementos.map(async (elemento) => {
            try {
              return { elemento, resumen: await api.resumen(elemento.id) };
            } catch {
              return { elemento, resumen: null };
            }
          }),
        );
        if (!cancelado) setElementos(conResumen);
      })
      .catch(() => {
        if (!cancelado) setError("No se pudieron cargar los datos de la obra.");
      });
    return () => {
      cancelado = true;
    };
  }, []);

  const obra = useMemo(
    () => obras?.find((o) => o.id === obraId) ?? null,
    [obras, obraId],
  );
  const elementosDeObra = useMemo(
    () => (elementos ?? []).filter((e) => e.elemento.obra === obraId),
    [elementos, obraId],
  );

  if (error) {
    return (
      <p role="alert" className="bg-fuera/10 border border-fuera text-[#94453a] rounded-lg px-4 py-3 text-sm font-medium">
        {error}
      </p>
    );
  }
  if (!obras || !elementos) {
    return <p className="text-tinta/60 py-10 text-center">Cargando panel de obra…</p>;
  }
  if (obras.length === 0) {
    return (
      <p className="text-tinta/60 py-10 text-center">
        No hay obras asignadas a tu contrata todavía.
      </p>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <label
          htmlFor="selector-obra"
          className="block text-sm font-semibold text-tinta/70 mb-1.5"
        >
          Obra
        </label>
        <select
          id="selector-obra"
          value={obraId ?? ""}
          onChange={(e) => setObraId(Number(e.target.value))}
          className="w-full sm:w-auto sm:min-w-72 text-base font-semibold rounded-lg border border-[#cfc6ba] bg-white px-4 py-3 focus:outline-none focus:ring-2 focus:ring-acento/40 focus:border-acento"
        >
          {obras.map((o) => (
            <option key={o.id} value={o.id}>
              {o.codigo}
            </option>
          ))}
        </select>
      </div>

      {obra && (
        <section className="bg-white border border-linea rounded-xl p-5 shadow-sm">
          <div className="flex flex-wrap items-start gap-3">
            <div className="flex-1 min-w-56">
              <h2 className="text-lg font-bold font-mono">{obra.codigo}</h2>
              <p className="text-sm text-tinta/70 mt-1">
                {obra.direccion || "Sin dirección"}
                {obra.ubicacion ? ` · ${obra.ubicacion}` : ""}
              </p>
              <p className="text-xs text-tinta/50 mt-1">
                Arquitectura {obra.arquitectura}
                {obra.requiere_otdr ? " · Requiere OTDR" : ""}
              </p>
            </div>
            <span className="inline-block text-[11px] font-semibold rounded-full border border-acento text-acento-oscuro bg-acento/10 px-2.5 py-0.5">
              {obra.estado}
            </span>
          </div>
        </section>
      )}

      <section>
        <h3 className="text-sm font-semibold uppercase tracking-wider text-tinta/60 mb-3">
          Elementos de red ({elementosDeObra.length})
        </h3>
        {elementosDeObra.length === 0 ? (
          <p className="text-tinta/60 bg-white border border-linea rounded-xl p-5 text-sm">
            Esta obra no tiene elementos de red registrados.
          </p>
        ) : (
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {elementosDeObra.map(({ elemento, resumen }) => {
              const semaforo = resumen
                ? semaforoDeResumen(resumen.por_nivel, resumen.fusiones_activas)
                : "NEUTRO";
              return (
                <Link
                  key={elemento.id}
                  to={`/elementos/${elemento.id}`}
                  className="block bg-white border border-linea rounded-xl p-4 shadow-sm hover:border-acento active:bg-arena/60 transition-colors"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-bold font-mono">{elemento.codigo}</p>
                      <p className="text-xs text-tinta/60 mt-0.5">
                        {etiquetaTipoElemento(elemento.tipo)}
                      </p>
                    </div>
                    <BadgeSemaforo nivel={semaforo} />
                  </div>
                  {elemento.direccion && (
                    <p className="text-sm text-tinta/70 mt-2 line-clamp-2">
                      {elemento.direccion}
                    </p>
                  )}
                  {resumen ? (
                    <p className="text-xs text-tinta/60 mt-3 border-t border-dashed border-linea pt-2">
                      {resumen.fusiones_activas} fusiones activas ·{" "}
                      <span className="text-[#4f734f] font-semibold">
                        {resumen.por_nivel.OK ?? 0} OK
                      </span>{" "}
                      ·{" "}
                      <span className="text-[#8a6420] font-semibold">
                        {resumen.por_nivel.WARNING ?? 0} avisos
                      </span>{" "}
                      ·{" "}
                      <span className="text-[#94453a] font-semibold">
                        {resumen.por_nivel.FUERA ?? 0} fuera
                      </span>
                    </p>
                  ) : (
                    <p className="text-xs text-tinta/40 mt-3 border-t border-dashed border-linea pt-2">
                      Resumen no disponible
                    </p>
                  )}
                </Link>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
