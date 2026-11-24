EQUIPO 8 - REDIS - ETAPA 3
Instrucciones de ejecución

1. Requisitos
   Docker Desktop con contenedores Linux.
   Archivos: docker-compose.yml, Dockerfile, requirements.txt,
   scripts/experimento_rendimiento.py y scripts/experimento_memoria.py.

2. Dataset
   Descargar REES46 desde:
   https://www.kaggle.com/datasets/mkechinov/ecommerce-events-history-in-cosmetics-shop
   Colocar el CSV elegido en data/ y nombrarlo eventos.csv.
   Usar el mismo archivo para ambos experimentos.

3. Iniciar Redis y Python
   Abrir PowerShell en la carpeta del proyecto:

   docker compose up -d --build
   docker exec redis-exp1 redis-cli PING

   La segunda instrucción debe responder PONG.

4. Crear muestras (método utilizado por el equipo)
   Ejecutar desde PowerShell, con los contenedores iniciados:

   docker compose exec experimento sh -c "head -n 100001 data/eventos.csv > data/muestra_100000.csv"
   docker compose exec experimento sh -c "head -n 500001 data/eventos.csv > data/muestra_500000.csv"
   docker compose exec experimento sh -c "head -n 1000001 data/eventos.csv > data/muestra_1000000.csv"

   Cada archivo conserva la cabecera y el número indicado de eventos.
   Confirmar que eventos.csv tenga al menos 1.000.000 de registros más la cabecera.

5. Experimento 1: rendimiento de escritura
   docker compose exec experimento python scripts/experimento_rendimiento.py --muestra 100000 --lotes 1 10 100 500 1000 --repeticiones 3

   Para repetir con otro tamaño, cambiar --muestra por 500000 o 1000000.
   Resultados: resultados/resultados.csv.

6. Experimento 2: consumo de memoria
   docker compose exec experimento python scripts/experimento_memoria.py --muestras 100000 500000 1000000 --repeticiones 3

   Compara Hash y String JSON con los mismos eventos.
   Resultados: resultados/resultados_memoria.csv.

7. Finalizar
   docker compose down

Notas
- Ejecutar los experimentos por separado: ambos limpian la base Redis.
- Redis usa la configuración del docker-compose.yml entregado (sin RDB ni AOF).
- El método head toma las primeras filas del CSV; no es una muestra aleatoria.
- Ajustar los tamaños de ejecución a los realmente probados y reportados en el informe.
- Repositorio.txt de la entrega debe contener la URL del repositorio GitHub.
