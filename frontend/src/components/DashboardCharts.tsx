import { MetricBucket, TimeMetricBucket } from "../api/client";
import { useI18n } from "../i18n";

const chartColors = ["#0b63ce", "#46a0f5", "#8bc5ff", "#c8e3ff", "#dbe4ee", "#64748b", "#22a06b", "#f59e0b"];

export function DonutChart({ title, data, centerLabel }: { title: string; data: MetricBucket[]; centerLabel: string }) {
  const { t } = useI18n();
  const total = data.reduce((sum, item) => sum + item.value, 0);
  let offset = 0;
  return <section className="dashboard-card chart-card">
    <div className="card-heading"><h2>{title}</h2></div>
    {!total ? <EmptyChart /> : <div className="donut-layout">
      <div className="donut" role="img" aria-label={`${title}: ${total}`}>
        <svg viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="45" fill="none" stroke="#edf1f5" strokeWidth="14" />
          {data.map((item, index) => {
            const portion = item.value / total * 100;
            const current = offset;
            offset += portion;
            return <circle key={item.label} cx="60" cy="60" r="45" fill="none" stroke={chartColors[index % chartColors.length]} strokeWidth="14" pathLength="100" strokeDasharray={`${portion} ${100 - portion}`} strokeDashoffset={-current} transform="rotate(-90 60 60)" />;
          })}
        </svg>
        <div className="donut__center"><strong>{total}</strong><span>{centerLabel}</span></div>
      </div>
      <div className="chart-legend">{data.slice(0, 6).map((item, index) => <div key={item.label}><span className="legend-dot" style={{ background: chartColors[index % chartColors.length] }} /><span className="legend-label">{formatLabel(item.label)}</span><strong>{item.value}</strong></div>)}</div>
    </div>}
    {!total && <span className="sr-only">{t("common.noData")}</span>}
  </section>;
}

export function HorizontalBars({ title, data }: { title: string; data: MetricBucket[] }) {
  const max = Math.max(1, ...data.map((item) => item.value));
  return <section className="dashboard-card chart-card">
    <div className="card-heading"><h2>{title}</h2></div>
    {!data.length ? <EmptyChart /> : <div className="horizontal-bars">{data.slice(0, 7).map((item) => <div className="horizontal-bar" key={item.label}>
      <div><span>{formatLabel(item.label)}</span><strong>{item.value}</strong></div>
      <div className="horizontal-bar__track"><span style={{ width: `${Math.max(3, item.value / max * 100)}%` }} /></div>
    </div>)}</div>}
  </section>;
}

export function TimelineChart({ title, data, locale }: { title: string; data: TimeMetricBucket[]; locale: string }) {
  const visible = data.slice(-18);
  const max = Math.max(1, ...visible.map((item) => item.value));
  const width = 600; const height = 170; const pad = 18;
  const points = visible.map((item, index) => `${visible.length === 1 ? width / 2 : pad + index * (width - pad * 2) / (visible.length - 1)},${height - pad - item.value / max * (height - pad * 2)}`).join(" ");
  const area = visible.length ? `${pad},${height - pad} ${points} ${width - pad},${height - pad}` : "";
  return <section className="dashboard-card chart-card timeline-card">
    <div className="card-heading"><h2>{title}</h2><span>{visible.reduce((sum, item) => sum + item.value, 0)} reports</span></div>
    {!visible.length ? <EmptyChart /> : <>
      <svg className="timeline-chart" viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none" role="img" aria-label={title}>
        {[0.25, .5, .75, 1].map((line) => <line key={line} x1={pad} x2={width - pad} y1={height - pad - line * (height - pad * 2)} y2={height - pad - line * (height - pad * 2)} stroke="#e8edf3" strokeWidth="1" />)}
        <polygon points={area} fill="rgba(11,99,206,.10)" />
        <polyline points={points} fill="none" stroke="#0b63ce" strokeWidth="3" vectorEffect="non-scaling-stroke" strokeLinejoin="round" strokeLinecap="round" />
      </svg>
      <div className="timeline-labels"><span>{formatTime(visible[0]?.bucket, locale)}</span><span>{formatTime(visible[Math.floor(visible.length / 2)]?.bucket, locale)}</span><span>{formatTime(visible[visible.length - 1]?.bucket, locale)}</span></div>
    </>}
  </section>;
}

function EmptyChart() { const { t } = useI18n(); return <div className="chart-empty">{t("common.noData")}</div>; }
function formatLabel(value: string) { return value.replace(/_/g, " "); }
function formatTime(value: string | undefined, locale: string) { return value ? new Date(value).toLocaleTimeString(locale, { hour: "2-digit", minute: "2-digit" }) : "—"; }
