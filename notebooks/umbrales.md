# Umbrales de scoring — notas de Valentina y Nico

> Esto era un notebook (`umbrales.ipynb`) con los histogramas de `score` contra
> operaciones marcadas como fraude confirmado por ops. Lo pasamos a Markdown para que
> no dependa de un kernel de Jupyter en el repo; los números y las conclusiones son
> los mismos que discutimos con el equipo.

## Contexto

Tomamos ~3 semanas de operaciones de staging con carga sintética (el generador de
tráfico) y les cruzamos las marcas manuales de ops sobre cuáles eran fraude. No es un
dataset gigante, pero alcanza para no elegir los umbrales a ojo.

## Por qué 60/40 entre Sentinel y velocidad

Sentinel ve señales que nosotros no tenemos (dispositivo, geolocalización, historial
cross-vendor). Confiamos más en su `risk` que en nuestra propia heurística de
velocidad, que es bastante primitiva (solo cuenta operaciones por cuenta origen, no
mira monto ni destino). De ahí el peso 0.6 para Sentinel y 0.4 para velocidad.

```
score = 0.6 * sentinel.risk + 0.4 * min(velocidad / 10, 1)
```

El `min(velocidad / 10, 1)` capea la componente de velocidad en 1: a partir de 10
operaciones en la ventana de 10 minutos, no suma más score adicional por velocidad.
Podría ser útil en algún momento no capear esto, pero por ahora una cuenta que hace 50
operaciones en 10 minutos no es "más sospechosa" que una que hace 10 — ya cruzó
cualquier umbral razonable de todos modos.

## Por qué esos cortes

- **`reject` en `>= 0.85`**: en nuestra muestra, por encima de ese score el 94% de las
  operaciones terminaron confirmadas como fraude por ops. Bajarlo más metía falsos
  positivos que ops nos pedía revisar a mano de todos modos, así que preferimos que
  caigan en `review`.
- **`review` en `>= 0.6`**: es el punto donde la señal de Sentinel sola (sin ninguna
  velocidad) ya empieza a valer la pena mirar (`sentinel.risk >= 1.0` con velocidad
  0 da exactamente 0.6). Por debajo de eso, dejamos pasar: el volumen de revisiones
  manuales que generaría no se justificaba con la tasa de fraude que encontrábamos.

## Cosas que no resolvimos todavía

- No tenemos memoria de "reincidencia": si una cuenta ya fue `review` la semana
  pasada, hoy arranca de cero.
- El score no distingue moneda ni monto directamente — Sentinel sí lo ve (se lo
  mandamos en el `POST /v2/assess`), pero nuestra propia velocidad no pondera por
  monto, solo cuenta operaciones.
- Nos falta reprocesar los umbrales con datos de prod real en vez de solo staging;
  todavía no tuvimos volumen suficiente ahí como para que valga la pena.
