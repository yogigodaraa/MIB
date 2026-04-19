export default function Home() {
  return (
    <main className="min-h-screen flex flex-col">
      {/* Hero */}
      <section className="flex-1 flex items-center justify-center px-6 py-24 relative overflow-hidden">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute -top-40 left-1/2 -translate-x-1/2 w-[800px] h-[600px] rounded-full opacity-20 blur-[120px]"
          style={{ background: "radial-gradient(ellipse at center, #3b82f6, #06b6d4 50%, transparent 80%)" }}
        />
        <div className="relative max-w-2xl text-center">
          <p className="text-xs uppercase tracking-widest text-zinc-500">Mooring Intelligence Backend</p>
          <h1 className="mt-4 text-5xl sm:text-6xl font-extrabold tracking-tight">
            <span className="bg-clip-text text-transparent" style={{ backgroundImage: "linear-gradient(135deg,#60a5fa,#22d3ee)" }}>
              MIB
            </span>
          </h1>
          <p className="mt-6 text-lg text-zinc-400 leading-relaxed">
            Real-time tension monitoring for BHP vessel mooring hooks. Predictive alerts,
            four-tier escalation, linear-regression forecasting, 3D movement tracking.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            <a href="https://github.com/yogigodaraa/MIB" target="_blank" rel="noopener noreferrer"
              className="rounded-full px-6 py-3 text-sm font-semibold text-white shadow-lg"
              style={{ backgroundImage: "linear-gradient(135deg,#3b82f6,#06b6d4)" }}>
              View on GitHub →
            </a>
            <a href="/docs" className="rounded-full px-6 py-3 text-sm font-semibold text-zinc-200 border border-zinc-700 hover:bg-zinc-900">
              API docs (Swagger)
            </a>
          </div>
        </div>
      </section>

      {/* Alert tiers */}
      <section className="px-6 py-16 border-t border-zinc-800">
        <div className="mx-auto max-w-4xl">
          <h2 className="text-2xl font-bold text-center">Alert tiers</h2>
          <div className="mt-8 grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Safe", range: "0–30%", color: "#22c55e" },
              { label: "Caution", range: "30–70%", color: "#eab308" },
              { label: "Warning", range: "70–85%", color: "#f97316" },
              { label: "Critical", range: "85%+", color: "#ef4444" },
            ].map((t) => (
              <div key={t.label} className="rounded-xl border border-zinc-800 bg-zinc-900/50 p-5">
                <div className="h-1.5 rounded-full" style={{ backgroundColor: t.color }} />
                <p className="mt-3 text-sm font-semibold" style={{ color: t.color }}>{t.label}</p>
                <p className="mt-1 text-xs text-zinc-500 font-mono">{t.range}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Stack */}
      <section className="px-6 py-16 border-t border-zinc-800">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-2xl font-bold">Tech stack</h2>
          <p className="mt-4 text-zinc-400">
            Python 3.10 · FastAPI · Pydantic · Uvicorn · Jinja2 · Linear-regression tension forecasting ·
            Outlier detection with calibration drift · Polling updates every 2–3s
          </p>
        </div>
      </section>

      <footer className="border-t border-zinc-800 px-6 py-8 text-center text-xs text-zinc-600">
        <p>
          Built by <a href="https://github.com/yogigodaraa" className="hover:text-zinc-400">Yogi</a>.
          Licensed MIT.
        </p>
      </footer>
    </main>
  );
}
