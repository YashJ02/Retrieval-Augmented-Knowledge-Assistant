import { UploadCard } from "@/components/UploadCard";

export default function UploadPage() {
  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">AutoDash</p>
        <h1>Upload data. Get a dashboard spec instantly.</h1>
        <p>
          Deterministic profiling, rule-based dataset intent inference, and server-generated chart SQL.
        </p>
        <div className="hero-grid">
          <div className="hero-chip">Rule Engine</div>
          <div className="hero-chip">JSON Contracts</div>
          <div className="hero-chip">DuckDB Execution</div>
          <div className="hero-chip">Zero Manual Charts</div>
        </div>
      </section>
      <UploadCard />
    </main>
  );
}

