// Selftest Governance Health Dashboard (Grafana Jsonnet)
// This dashboard provides comprehensive monitoring of the selftest system
// across all environments (dev, staging, prod) with tier-aware metrics.

local grafana = import 'grafonnet/grafana.libsonnet';
local dashboard = grafana.dashboard;
local row = grafana.row;
local singlestat = grafana.singlestat;
local graphPanel = grafana.graphPanel;
local tablePanel = grafana.tablePanel;
local heatmapPanel = grafana.heatmapPanel;
local prometheus = grafana.prometheus;

dashboard.new(
  'Selftest Governance Health',
  tags=['selftest', 'platform', 'governance'],
  timezone='browser',
  refresh='1m',
  time_from='now-7d',
  editable=true,
)

.addTemplate(
  grafana.template.datasource(
    'datasource',
    'prometheus',
    'Prometheus',
    hide='',
  )
)

.addTemplate(
  grafana.template.new(
    'environment',
    '$datasource',
    'label_values(selftest_step_total, environment)',
    label='Environment',
    refresh='load',
    multi=true,
    includeAll=true,
  )
)

// Row 1: Overall Health Status
.addPanel(
  singlestat.new(
    'Overall Status',
    datasource='$datasource',
    format='short',
    valueName='current',
    sparklineShow=false,
    gaugeShow=true,
    gaugeMinValue=0,
    gaugeMaxValue=1,
    thresholds='0.3,0.7',
    colors=['red', 'yellow', 'green'],
    valueMaps=[
      { value: '0', text: 'BROKEN', op: '=' },
      { value: '0.5', text: 'DEGRADED', op: '=' },
      { value: '1', text: 'HEALTHY', op: '=' },
    ],
  )
  .addTarget(
    prometheus.target(
      'selftest_run_overall_status{environment=~"$environment"}',
      legendFormat='{{environment}}',
    )
  ), gridPos={
    x: 0,
    y: 0,
    w: 6,
    h: 8,
  }
)

.addPanel(
  graphPanel.new(
    'Governance Pass Rate (%)',
    datasource='$datasource',
    format='percent',
    min=0,
    max=100,
    fill=2,
    linewidth=2,
    bars=false,
    lines=true,
    staircase=false,
    decimals=2,
  )
  .addTarget(
    prometheus.target(
      'selftest_governance_pass_rate{environment=~"$environment"}',
      legendFormat='{{environment}}',
    )
  )
  .addSeriesOverride({
    alias: 'prod',
    color: '#37872D',
    linewidth: 3,
  })
  .addSeriesOverride({
    alias: 'staging',
    color: '#FADE2A',
  })
  .addSeriesOverride({
    alias: 'dev',
    color: '#5794F2',
  })
  .addThreshold({
    value: 95,
    colorMode: 'critical',
    op: 'lt',
    fill: true,
    line: true,
    yaxis: 'left',
  }), gridPos={
    x: 6,
    y: 0,
    w: 18,
    h: 8,
  }
)

// Row 2: Active Degradations and Failure Analysis
.addPanel(
  singlestat.new(
    'Active Degradations',
    datasource='$datasource',
    format='short',
    valueName='current',
    sparklineShow=false,
    gaugeShow=false,
    thresholds='1,5',
    colors=['green', 'yellow', 'red'],
  )
  .addTarget(
    prometheus.target(
      'sum(selftest_degradations_active{environment=~"$environment"})',
      legendFormat='Active',
    )
  ), gridPos={
    x: 0,
    y: 8,
    w: 6,
    h: 4,
  }
)

.addPanel(
  graphPanel.new(
    'Step Failure Distribution (Top 5)',
    datasource='$datasource',
    format='short',
    bars=true,
    lines=false,
    legend_show=true,
    legend_alignAsTable=true,
    legend_rightSide=true,
    legend_values=true,
    legend_current=true,
    legend_sort='current',
    legend_sortDesc=true,
  )
  .addTarget(
    prometheus.target(
      'topk(5, sum by (step_id) (rate(selftest_step_failures_total{environment=~"$environment"}[5m])))',
      legendFormat='{{step_id}}',
    )
  ), gridPos={
    x: 6,
    y: 8,
    w: 18,
    h: 8,
  }
)

// Row 3: Performance Metrics
.addPanel(
  graphPanel.new(
    'Run Duration Distribution (P50, P95, P99)',
    datasource='$datasource',
    format='s',
    fill=1,
    linewidth=2,
    legend_show=true,
    legend_alignAsTable=true,
    legend_values=true,
    legend_current=true,
    legend_avg=true,
  )
  .addTarget(
    prometheus.target(
      'histogram_quantile(0.50, rate(selftest_run_duration_seconds_bucket{environment=~"$environment"}[5m]))',
      legendFormat='P50 - {{environment}}',
    )
  )
  .addTarget(
    prometheus.target(
      'histogram_quantile(0.95, rate(selftest_run_duration_seconds_bucket{environment=~"$environment"}[5m]))',
      legendFormat='P95 - {{environment}}',
    )
  )
  .addTarget(
    prometheus.target(
      'histogram_quantile(0.99, rate(selftest_run_duration_seconds_bucket{environment=~"$environment"}[5m]))',
      legendFormat='P99 - {{environment}}',
    )
  )
  .addThreshold({
    value: 60,
    colorMode: 'custom',
    fillColor: 'rgba(255, 255, 0, 0.2)',
    op: 'gt',
    line: true,
    lineColor: 'yellow',
  })
  .addThreshold({
    value: 120,
    colorMode: 'critical',
    op: 'gt',
    line: true,
  }), gridPos={
    x: 0,
    y: 16,
    w: 24,
    h: 8,
  }
)

// Row 4: Heatmap and AC Pass Rates
.addPanel(
  heatmapPanel.new(
    'Step Failures Heatmap',
    datasource='$datasource',
    dataFormat='tsbuckets',
    color_mode='spectrum',
    color_colorScheme='interpolateRdYlGn',
    color_exponent=0.5,
    yAxis_format='short',
    yAxis_decimals=0,
    hideZeroBuckets=true,
  )
  .addTarget(
    prometheus.target(
      'sum by (step_id, severity) (rate(selftest_step_failures_total{environment=~"$environment"}[1h]))',
      format='time_series',
    )
  ), gridPos={
    x: 0,
    y: 24,
    w: 16,
    h: 10,
  }
)

.addPanel(
  tablePanel.new(
    'Acceptance Criteria Pass Rates',
    datasource='$datasource',
    transform='timeseries_to_rows',
    styles=[
      {
        pattern: 'Time',
        type: 'hidden',
      },
      {
        pattern: 'ac_id',
        type: 'string',
        alias: 'AC ID',
      },
      {
        pattern: 'Value',
        type: 'number',
        alias: 'Pass Rate (%)',
        decimals: 2,
        unit: 'percent',
        thresholds: [95, 100],
        colorMode: 'cell',
        colors: ['red', 'yellow', 'green'],
      },
    ],
  )
  .addTarget(
    prometheus.target(
      'selftest_ac_pass_rate{environment=~"$environment"}',
      format='table',
      instant=true,
    )
  ), gridPos={
    x: 16,
    y: 24,
    w: 8,
    h: 10,
  }
)

// Row 5: Detailed Step Analysis
.addPanel(
  graphPanel.new(
    'Step Duration by Tier',
    datasource='$datasource',
    format='s',
    legend_show=true,
    legend_alignAsTable=true,
    legend_rightSide=false,
    legend_values=true,
    legend_avg=true,
    legend_max=true,
    stack=false,
  )
  .addTarget(
    prometheus.target(
      'avg by (step_id, tier) (rate(selftest_step_duration_seconds_sum{environment=~"$environment"}[5m]) / rate(selftest_step_duration_seconds_count{environment=~"$environment"}[5m]))',
      legendFormat='{{step_id}} ({{tier}})',
    )
  ), gridPos={
    x: 0,
    y: 34,
    w: 24,
    h: 8,
  }
)

// Row 6: SLO Compliance Indicators
.addPanel(
  singlestat.new(
    'Availability SLO',
    description='Target: 99% of runs complete successfully',
    datasource='$datasource',
    format='percentunit',
    valueName='current',
    sparklineShow=true,
    sparklineFull=true,
    gaugeShow=true,
    gaugeMinValue=0,
    gaugeMaxValue=1,
    thresholds='0.95,0.99',
    colors=['red', 'yellow', 'green'],
  )
  .addTarget(
    prometheus.target(
      'sum(rate(selftest_step_total{environment="prod"}[30d])) / (sum(rate(selftest_step_total{environment="prod"}[30d])) + sum(rate(selftest_step_failures_total{environment="prod"}[30d])))',
      legendFormat='Availability',
    )
  ), gridPos={
    x: 0,
    y: 42,
    w: 8,
    h: 6,
  }
)

.addPanel(
  singlestat.new(
    'Performance SLO',
    description='Target: P95 run duration <= 120s',
    datasource='$datasource',
    format='s',
    valueName='current',
    sparklineShow=true,
    sparklineFull=true,
    gaugeShow=true,
    gaugeMinValue=0,
    gaugeMaxValue=150,
    thresholds='90,120',
    colors=['green', 'yellow', 'red'],
  )
  .addTarget(
    prometheus.target(
      'histogram_quantile(0.95, rate(selftest_run_duration_seconds_bucket{environment="prod"}[30d]))',
      legendFormat='P95 Duration',
    )
  ), gridPos={
    x: 8,
    y: 42,
    w: 8,
    h: 6,
  }
)

.addPanel(
  singlestat.new(
    'Degradation SLO',
    description='Target: No more than 3 repeated degradations per step in 24h',
    datasource='$datasource',
    format='short',
    valueName='current',
    sparklineShow=true,
    sparklineFull=true,
    gaugeShow=true,
    gaugeMinValue=0,
    gaugeMaxValue=5,
    thresholds='3,5',
    colors=['green', 'yellow', 'red'],
  )
  .addTarget(
    prometheus.target(
      'max by (step_id) (sum_over_time(selftest_degradations_total{environment="prod"}[24h]))',
      legendFormat='Max Degradations',
    )
  ), gridPos={
    x: 16,
    y: 42,
    w: 8,
    h: 6,
  }
)
