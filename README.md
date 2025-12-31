# Herramienta para preparar la renta (España) para inversiones en bolsa (Schwab)

Ayuda a preparar la renta (España) para inversiones en bolsa (Schwab).

## Modelo 100

### Lógica fiscal (la que implementa la herramienta)

Criterio de fechas:

- Dividendos: tipo de cambio por Date de la transacción.
  ​- Ventas (realized): tipo de cambio por Closed Date.
  ​
  Si no hay fixing ese día (finde/festivo): usar el último disponible anterior (forward-fill al construir el calendario diario).
  ​
  Conversión:

BCE publica “USD por 1 EUR” por lo que

$EUR = \dfrac{USD}{USD_{eur}}$

[Source](https://www.ecb.europa.eu/stats/policy_and_exchange_rates/euro_reference_exchange_rates/html/index.en.html)

## Input

Hay que extraer los CSV de Schwab de la siguiente manera.

- Dividendos:

<div align="center">

![Dividendos](img/transaction_history.png)

</div>

- Plusvalias (Compra/venta de acciones):

<div align="center">

![Plusvalias](img/realizaed_gain_loss.png)

</div>

Dejamos los ficheros de entrada en la carpeta data/.

- data/Indiviual_XXX*\_Transactions_2025*.csv (Dividendos)
- data/XXX*\_GainLoss_Realized_Details2025*.csv (Ventas)

## Outpout

Salida (por defecto):

- out/resumen_anual_2025.csv
- out/desglose_symbol_2025.csv


## Modelo 720

## Input

A fecha 31 de diciembre del año en cuestión,
Hay que extraer un único CSV de Schwab de la siguiente manera.

<div align="center">

![Modelo 720](img/720.png)

</div>

Dejamos el fichero de entrada en la carpeta data/.

- data/Individual-Positions-2025-12-31-*.csv

## Outpout

Salida (por defecto):

- out/modelo_720_2025.csv