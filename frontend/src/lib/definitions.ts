// Metric definitions shown in hover tooltips, kept in one place so wording stays consistent.
export const DEFINITIONS = {
  gateClosure: 'Forecasts published after this time on the decision date are excluded. Default 09:20 UTC is EPEX GB day-ahead auction gate closure.',
  forecastRun: 'Latest Elexon WINDFOR forecast published at or before gate closure.',
  leadTime: 'Hours between forecast publication and the start of the delivery date.',
  mae: 'Mean absolute error: average size of the hourly forecast miss.',
  rmse: 'Root mean square error: like MAE but weights large misses more heavily.',
  bias: 'Mean of forecast − outturn. Positive = over-forecast (less wind than forecast).',
  wape: 'Weighted absolute percentage error: total absolute error ÷ total outturn.',
  distribution: 'Percentiles of hourly error (forecast − outturn) across all delivery dates.',
} as const
