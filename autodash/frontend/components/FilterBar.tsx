"use client";

import { useEffect, useMemo, useState } from "react";

import type { FilterSpec, FilterValues } from "@/lib/types";

interface FilterBarProps {
  filters: FilterSpec[];
  onApply: (values: FilterValues) => void;
}

type FilterDraft = Record<string, unknown>;

export function FilterBar({ filters, onApply }: FilterBarProps) {
  const [draft, setDraft] = useState<FilterDraft>({});
  const [expanded, setExpanded] = useState(true);
  const [autoApply, setAutoApply] = useState(false);

  const hasFilters = filters.length > 0;
  const serializedDraft = useMemo(() => JSON.stringify(draft), [draft]);

  useEffect(() => {
    if (!autoApply) return;
    const timeout = setTimeout(() => onApply(draft), 250);
    return () => clearTimeout(timeout);
  }, [autoApply, draft, onApply]);

  function setDateBoundary(filterId: string, boundary: "start" | "end", value: string): void {
    const current = (draft[filterId] as Record<string, unknown>) ?? {};
    setDraft((prev) => ({
      ...prev,
      [filterId]: {
        ...current,
        [boundary]: value
      }
    }));
  }

  function setNumericBoundary(filterId: string, boundary: "min" | "max", value: string): void {
    const parsed = value === "" ? undefined : Number(value);
    const current = (draft[filterId] as Record<string, unknown>) ?? {};
    setDraft((prev) => ({
      ...prev,
      [filterId]: {
        ...current,
        [boundary]: parsed
      }
    }));
  }

  function setCategoricalValues(filterId: string, selectedValues: string[]): void {
    setDraft((prev) => ({ ...prev, [filterId]: selectedValues }));
  }

  function resetFilters(): void {
    setDraft({});
    onApply({});
  }

  if (!hasFilters) {
    return (
      <section className="filter-panel">
        <div className="panel-headline">Filters</div>
        <p>No dynamic filters were generated for this dataset.</p>
      </section>
    );
  }

  return (
    <section className="filter-panel">
      <div className="filter-title-row">
        <div className="panel-headline">Filters</div>
        <div className="filter-header-actions">
          <small className="draft-state" key={serializedDraft}>
            {Object.keys(draft).length} selected
          </small>
          <button type="button" className="icon-btn ghost" onClick={() => setExpanded((value) => !value)}>
            {expanded ? "Collapse" : "Expand"}
          </button>
        </div>
      </div>

      {expanded ? (
        <>
          <div className="filter-grid">
            {filters.map((filter) => {
              if (filter.type === "date_range") {
                const current = (draft[filter.filter_id] as Record<string, string | undefined>) ?? {};
                return (
                  <div className="filter-item" key={filter.filter_id}>
                    <label>{filter.label}</label>
                    <div className="range-inputs">
                      <input
                        type="date"
                        min={String(filter.min ?? "")}
                        max={String(filter.max ?? "")}
                        value={current.start ?? ""}
                        onChange={(event) => setDateBoundary(filter.filter_id, "start", event.target.value)}
                      />
                      <input
                        type="date"
                        min={String(filter.min ?? "")}
                        max={String(filter.max ?? "")}
                        value={current.end ?? ""}
                        onChange={(event) => setDateBoundary(filter.filter_id, "end", event.target.value)}
                      />
                    </div>
                  </div>
                );
              }

              if (filter.type === "numeric_range") {
                const current = (draft[filter.filter_id] as Record<string, number | undefined>) ?? {};
                return (
                  <div className="filter-item" key={filter.filter_id}>
                    <label>{filter.label}</label>
                    <div className="range-inputs">
                      <input
                        type="number"
                        step="any"
                        min={typeof filter.min === "number" ? filter.min : undefined}
                        max={typeof filter.max === "number" ? filter.max : undefined}
                        value={typeof current.min === "number" ? current.min : ""}
                        onChange={(event) =>
                          setNumericBoundary(filter.filter_id, "min", event.target.value)
                        }
                      />
                      <input
                        type="number"
                        step="any"
                        min={typeof filter.min === "number" ? filter.min : undefined}
                        max={typeof filter.max === "number" ? filter.max : undefined}
                        value={typeof current.max === "number" ? current.max : ""}
                        onChange={(event) =>
                          setNumericBoundary(filter.filter_id, "max", event.target.value)
                        }
                      />
                    </div>
                  </div>
                );
              }

              const selected = (draft[filter.filter_id] as string[]) ?? [];
              return (
                <div className="filter-item" key={filter.filter_id}>
                  <label>{filter.label}</label>
                  <select
                    multiple
                    value={selected}
                    onChange={(event) =>
                      setCategoricalValues(
                        filter.filter_id,
                        Array.from(event.target.selectedOptions).map((option) => option.value)
                      )
                    }
                  >
                    {filter.options.map((option) => (
                      <option value={option} key={option}>
                        {option}
                      </option>
                    ))}
                  </select>
                </div>
              );
            })}
          </div>

          <div className="filter-actions">
            <button type="button" onClick={() => onApply(draft)} disabled={autoApply}>
              Apply Filters
            </button>
            <button type="button" className="ghost" onClick={resetFilters}>
              Reset
            </button>
            <label className="toggle-label">
              <input
                type="checkbox"
                checked={autoApply}
                onChange={(event) => setAutoApply(event.target.checked)}
              />
              Auto-apply
            </label>
          </div>
        </>
      ) : null}
    </section>
  );
}

