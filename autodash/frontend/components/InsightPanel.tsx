"use client";

import { useState } from "react";

import type { InsightItem } from "@/lib/types";

interface InsightPanelProps {
  insights: InsightItem[];
}

export function InsightPanel({ insights }: InsightPanelProps) {
  const [expandedId, setExpandedId] = useState<string | null>(insights[0]?.insight_id ?? null);

  return (
    <section className="insight-panel">
      <div className="panel-headline">Insights Engine</div>
      <ul>
        {insights.map((insight) => (
          <li key={insight.insight_id} className="insight-item">
            <button
              type="button"
              className="insight-trigger"
              onClick={() =>
                setExpandedId((current) => (current === insight.insight_id ? null : insight.insight_id))
              }
            >
              <strong>{insight.title}</strong>
              <small className={`badge ${insight.severity}`}>{insight.severity}</small>
            </button>
            {expandedId === insight.insight_id ? <p>{insight.description}</p> : null}
          </li>
        ))}
      </ul>
    </section>
  );
}

