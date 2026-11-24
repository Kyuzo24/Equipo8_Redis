import argparse
import csv
import os
import statistics
import time

import redis


def leer_eventos(ruta):
    """Lee el CSV completo en memoria. Esta lectura NO se mide."""
    eventos = []
    with open(ruta, newline="", encoding="utf-8") as f:
        for fila in csv.DictReader(f):
            # Redis no acepta valores None: se reemplazan por texto vacío
            eventos.append({k: (v or "") for k, v in fila.items() if k is not None})
    return eventos


def cargar(r, eventos, lote, transaccion):
    """Envía todos los eventos a Redis y devuelve los segundos que tardó."""
    inicio = time.perf_counter()
    if lote == 1:
        # Comando individual: un viaje de red por cada evento (sin pipeline)
        for i, ev in enumerate(eventos):
            r.hset(f"evento:{i}", mapping=ev)
    else:
        # Pipeline: se acumulan 'lote' comandos y se envían juntos
        pipe = r.pipeline(transaction=transaccion)
        for i, ev in enumerate(eventos):
            pipe.hset(f"evento:{i}", mapping=ev)
            if (i + 1) % lote == 0:
                pipe.execute()
        pipe.execute()  # envía el resto que quedó sin completar un lote
    return time.perf_counter() - inicio


def main():
    p = argparse.ArgumentParser(description="Experimento 1: rendimiento de escritura en Redis")
    p.add_argument("--muestra", type=int, required=True,
                   help="tamaño de la muestra (usa data/muestra_<N>.csv)")
    p.add_argument("--lotes", type=int, nargs="+", default=[1, 10, 100, 500, 1000],
                   help="tamaños de lote a probar (1 = sin pipeline)")
    p.add_argument("--repeticiones", type=int, default=3)
    p.add_argument("--transaccion", action="store_true",
                   help="usa pipeline con MULTI/EXEC")
    args = p.parse_args()

    ruta = f"data/muestra_{args.muestra}.csv"
    host = os.environ.get("REDIS_HOST", "localhost")
    r = redis.Redis(host=host, port=6379)
    r.ping()

    print(f"Leyendo {ruta} ...")
    eventos = leer_eventos(ruta)
    n = len(eventos)
    print(f"{n} eventos en memoria. Redis conectado en {host}.\n")

    filas = []
    medianas = {}
    for lote in args.lotes:
        if lote == 1:
            modo = "individual"
        elif args.transaccion:
            modo = "pipeline+transaccion"
        else:
            modo = "pipeline"

        tasas = []
        for rep in range(1, args.repeticiones + 1):
            r.flushall()  # base vacía antes de cada medición
            seg = cargar(r, eventos, lote, args.transaccion)
            claves = r.dbsize()
            ok = claves == n
            tasa = n / seg
            tasas.append(tasa)
            print(f"lote={lote:<5} rep={rep}  {seg:8.2f} s  {tasa:12.0f} eventos/s  "
                  f"claves={claves}  {'OK' if ok else 'ERROR: faltan datos'}")
            filas.append([time.strftime("%Y-%m-%d %H:%M:%S"), n, lote, modo, rep,
                          round(seg, 4), round(tasa, 1), claves, ok])
        medianas[lote] = statistics.median(tasas)
    r.flushall()

    # Guardar todas las mediciones en resultados/resultados.csv
    os.makedirs("resultados", exist_ok=True)
    ruta_csv = "resultados/resultados.csv"
    nuevo = not os.path.exists(ruta_csv)
    with open(ruta_csv, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if nuevo:
            w.writerow(["fecha", "muestra", "lote", "modo", "repeticion",
                        "segundos", "eventos_por_seg", "claves_en_redis", "ok"])
        w.writerows(filas)

    # Tabla resumen con la mediana
    print(f"\nRESUMEN (mediana de {args.repeticiones} repeticiones, muestra = {n} eventos)")
    print(f"{'lote':>6} | {'eventos/s':>12} | {'vs lote 1':>9}")
    base = medianas.get(1)
    for lote, m in medianas.items():
        rel = f"{m / base:.1f}x" if base else "-"
        print(f"{lote:>6} | {m:12.0f} | {rel:>9}")
    print(f"\nMediciones guardadas en {ruta_csv}")


if __name__ == "__main__":
    main()
