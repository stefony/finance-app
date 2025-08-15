import React, { useState, useMemo } from "react";
import Papa from "papaparse";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

const API = "http://127.0.0.1:8000";

export default function App() {
  // UI state
  const [mode, setMode] = useState("returns"); // "returns" | "prices"
  const [textInput, setTextInput] = useState("0.01,-0.02,0.015,0.005,-0.01,0.02");
  const [lambda_, setLambda] = useState(0.94);
  const [series, setSeries] = useState([0.01, -0.02, 0.015, 0.005, -0.01, 0.02]);
  const [histVol, setHistVol] = useState(null);
  const [ewmaVol, setEwmaVol] = useState(null);
  const [error, setError] = useState("");

  // -------- CSV helpers --------
  const parseCsvToArray = (file) =>
    new Promise((resolve, reject) => {
      Papa.parse(file, {
        header: true,
        dynamicTyping: true,
        skipEmptyLines: true,
        complete: (res) => {
          const rows = res.data;
          if (!rows.length) return resolve([]);

          // вземаме ПЪРВАТА числова колона
          const keys = Object.keys(rows[0]);
          let col = null;
          for (const k of keys) {
            if (typeof rows[0][k] === "number") {
              col = k;
              break;
            }
          }
          if (!col) return reject(new Error("Не намерих числова колона в CSV."));
          const arr = rows.map((r) => Number(r[col])).filter((x) => Number.isFinite(x));
          resolve(arr);
        },
        error: (err) => reject(err),
      });
    });

  const parseManualInput = (txt) =>
    txt
      .split(/[,\s;]+/g)
      .map((x) => Number(x))
      .filter((x) => Number.isFinite(x));

  const handleCsv = async (e) => {
    setError("");
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const arr = await parseCsvToArray(file);
      setSeries(arr);
      setTextInput(arr.join(","));
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  // -------- Calculate --------
  const calculate = async () => {
    setError("");
    try {
      const arr = parseManualInput(textInput);
      if (!arr.length) throw new Error("Въведи поне едно число.");
      setSeries(arr);

      let url = "";
      let payload = {};
      if (mode === "returns") {
        url = `${API}/calc/volatility`;
        payload = { returns: arr, lambda_: Number(lambda_) };
      } else {
        url = `${API}/calc/volatility_from_prices`;
        payload = { prices: arr, lambda_: Number(lambda_) };
      }

      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || res.statusText);
      }
      const data = await res.json();
      setHistVol(data.hist_vol ?? null);
      setEwmaVol(data.ewma_vol ?? null);
    } catch (err) {
      setError(err.message || String(err));
    }
  };

  // -------- Chart data & formatting --------
  const chartData = series.map((v, i) => ({ t: `t${i + 1}`, value: v }));

  // Динамичен домейн за ос Y според режима
  const yDomain = useMemo(() => {
    if (!series.length) return ["auto", "auto"];
    const min = Math.min(...series);
    const max = Math.max(...series);

    if (mode === "prices") {
      // малък padding (≈2%) за цени
      const pad = Math.max((max - min) * 0.02, (max || min || 1) * 0.0005);
      return [min - pad, max + pad];
    } else {
      // по-широк padding за доходности
      const pad = Math.max((max - min) * 0.1, 0.001);
      return [min - pad, max + pad];
    }
  }, [series, mode]);

  const fmtY = (v) => (mode === "prices" ? v.toFixed(2) : `${(v * 100).toFixed(2)}%`);

  return (
    <div style={{ maxWidth: 1100, margin: "30px auto", padding: "0 10px" }}>
      <h1>Volatility Calculator</h1>

      {/* Mode toggle */}
      <div style={{ marginBottom: 10 }}>
        <label style={{ marginRight: 14 }}>
          <input
            type="radio"
            name="mode"
            value="returns"
            checked={mode === "returns"}
            onChange={() => setMode("returns")}
          />{" "}
          Returns
        </label>
        <label>
          <input
            type="radio"
            name="mode"
            value="prices"
            checked={mode === "prices"}
            onChange={() => setMode("prices")}
          />{" "}
          Prices
        </label>
      </div>

      {/* Inputs */}
      <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            {mode === "returns" ? "Returns (comma separated):" : "Prices (comma separated):"}
          </div>
          <input
            style={{ width: "100%" }}
            value={textInput}
            onChange={(e) => setTextInput(e.target.value)}
            placeholder={mode === "returns" ? "0.01,-0.02,..." : "100,101,99.5,..."}
          />
        </div>
        <div>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>Lambda:</div>
          <input
            style={{ width: 120 }}
            value={lambda_}
            onChange={(e) => setLambda(e.target.value)}
          />
        </div>
        <button onClick={calculate}>Calculate</button>
      </div>

      {/* CSV hint + uploader */}
      <div style={{ fontSize: 13, marginBottom: 8 }}>
        CSV: една числова колона (първа срещната). Ако са цени и си в режим “Prices”, бекендът сам ще
        изчисли доходностите.
      </div>
      <input type="file" accept=".csv" onChange={handleCsv} />

      {error && (
        <div style={{ color: "crimson", marginTop: 10 }}>
          Възникна грешка: {error}
        </div>
      )}

      {/* Chart */}
      <div style={{ height: 420, marginTop: 16 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 20, right: 16, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="t" />
            <YAxis domain={yDomain} tickFormatter={fmtY} />
            <Tooltip
              formatter={(value) =>
                mode === "prices" ? Number(value).toFixed(2) : `${(value * 100).toFixed(2)}%`
              }
              labelFormatter={(label) => label}
            />
            <Legend />
            <Line
              type="monotone"
              dataKey="value"
              name={mode === "returns" ? "Return" : "Price"}
              dot
            />
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* KPIs */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginTop: 18 }}>
        <div style={{ background: "#f7f9fc", padding: 16, borderRadius: 8 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Historical Volatility (σ)</div>
          <div style={{ fontSize: 28 }}>
            {histVol != null ? Number(histVol).toFixed(6) : "—"}
          </div>
        </div>
        <div style={{ background: "#f7f9fc", padding: 16, borderRadius: 8 }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>EWMA Volatility</div>
          <div style={{ fontSize: 28 }}>
            {ewmaVol != null ? Number(ewmaVol).toFixed(6) : "—"}
          </div>
        </div>
      </div>
    </div>
  );
}
