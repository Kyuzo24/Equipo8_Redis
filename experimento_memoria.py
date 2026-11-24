"""Experimento 2 - Consumo de memoria con HASH vs STRING JSON.
Uso: python scripts/experimento_memoria.py --muestras 10000 30000 100000 --repeticiones 3
Conecta SOLO al Redis dedicado de Docker Compose; FLUSHALL borra todas las claves.
"""
import argparse
import csv
import json
import os
import statistics
import time
from pathlib import Path
import redis


def leer_muestra(ruta, limite):
    eventos = []
    with open(ruta, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Igual que el experimento de rendimiento del compañero
            eventos.append({k: (v or '') for k, v in row.items() if k is not None})
            if len(eventos) >= limite:
                break
    return eventos


def cargar(r, eventos, modo, lote):
    pipe = r.pipeline(transaction=False)
    for i, ev in enumerate(eventos):
        key = f'evento:{i}'
        if modo == 'hash':
            pipe.hset(key, mapping=ev)
        else:
            pipe.set(key, json.dumps(ev, ensure_ascii=False, separators=(',', ':')))
        if (i + 1) % lote == 0:
            pipe.execute()
    pipe.execute()


def main():
    p = argparse.ArgumentParser(description='Experimento 2: memoria de HASH contra JSON como STRING')
    p.add_argument('--muestras', nargs='+', type=int, default=[10000, 30000, 100000])
    p.add_argument('--repeticiones', type=int, default=3)
    p.add_argument('--lote', type=int, default=500)
    args = p.parse_args()
    if not args.muestras or any(n <= 0 for n in args.muestras) or args.repeticiones < 1 or args.lote < 1:
        p.error('Las muestras, repeticiones y el lote deben ser positivos.')

    host = os.getenv('REDIS_HOST', 'localhost')
    r = redis.Redis(host=host, port=6379, decode_responses=True)
    r.ping()
    print('Redis conectado:', host)
    resultados = []
    for n in args.muestras:
        ruta = Path(f'data/muestra_{n}.csv')
        if not ruta.exists():
            raise SystemExit(f'Falta {ruta}; revisa la guia de preparacion de muestras.')
        eventos = leer_muestra(ruta, n)
        if len(eventos) != n:
            raise SystemExit(f'{ruta} tiene {len(eventos)} eventos; se esperaban {n}.')
        if not all(ev for ev in eventos):
            raise SystemExit(f'{ruta} incluye una fila sin campos; revisar dataset.')
        print(f'\nMuestra {n} eventos; campos: {list(eventos[0])}')
        for modo in ('hash', 'json_string'):
            for rep in range(1, args.repeticiones + 1):
                # Redis exclusivo del proyecto. NUNCA dirigirlo a un servidor compartido.
                r.flushall()
                memoria_base = r.info('memory')['used_memory']
                t0 = time.perf_counter()
                cargar(r, eventos, modo, args.lote)
                segundos = time.perf_counter() - t0
                claves = r.dbsize()
                memoria_final = r.info('memory')['used_memory']
                incremento = memoria_final - memoria_base
                ok = (claves == n)
                if not ok:
                    raise RuntimeError(f'Faltan claves: {claves}/{n} en modo {modo}')
                fila = [time.strftime('%Y-%m-%d %H:%M:%S'), n, modo, rep,
                        args.lote, memoria_base, memoria_final, incremento,
                        round(incremento / n, 3), round(segundos, 4), claves, ok]
                resultados.append(fila)
                print(f'{modo:12} rep={rep} memoria={incremento / 1024**2:.2f} MiB '
                      f'({incremento/n:.1f} B/evento) tiempo={segundos:.2f}s claves={claves}')
            r.flushall()
        del eventos

    os.makedirs('resultados', exist_ok=True)
    salida = Path('resultados/resultados_memoria.csv')
    # Sobrescribe cada corrida para que la tabla no mezcle ejecuciones anteriores.
    with salida.open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['fecha', 'muestra', 'modo', 'repeticion', 'lote', 'memoria_base_bytes',
                    'memoria_final_bytes', 'memoria_extra_bytes', 'bytes_por_evento',
                    'segundos_carga', 'claves_en_redis', 'ok'])
        w.writerows(resultados)

    print('\nRESUMEN: mediana de bytes/evento por configuracion')
    for n in args.muestras:
        for modo in ('hash', 'json_string'):
            vals = [fila[8] for fila in resultados if fila[1] == n and fila[2] == modo]
            print(f'{n:>9} {modo:12} -> {statistics.median(vals):>10.1f} B/evento')
    print('\nCSV guardado:', salida)
    print('ATENCION: este programa vacia Redis entre configuraciones.')


if __name__ == '__main__':
    main()
