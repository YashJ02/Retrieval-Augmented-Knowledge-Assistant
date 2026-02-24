import type { KPIItem } from "@/lib/types";

interface KPIGridProps {
  items: KPIItem[];
}

function formatValue(item: KPIItem): string {
  if (item.format === "percent") {
    return `${item.value.toFixed(2)}%`;
  }
  return Intl.NumberFormat("en-US", { maximumFractionDigits: 2 }).format(item.value);
}

export function KPIGrid({ items }: KPIGridProps) {
  return (
    <section className="kpi-grid">
      {items.map((item, index) => {
        const tone = item.format === "percent" ? "signal" : "neutral";
        return (
          <article key={item.kpi_id} className={`kpi-card ${tone} tone-${index % 5}`}>
            <div className="kpi-top-row">
              <span className="kpi-label">{item.title}</span>
              <small className="kpi-index">#{index + 1}</small>
            </div>
            <strong className="kpi-value">{formatValue(item)}</strong>
            {item.description ? <small>{item.description}</small> : <small>Computed server-side</small>}
          </article>
        );
      })}
    </section>
  );
}

