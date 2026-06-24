"use client";

import React from "react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from "recharts";

type ChartConfig = {
  chart_type?: string;
  x_axis?: string;
  y_axis?: string;
  title?: string;
};

type ChartProps = {
  config: ChartConfig;
  data: any[];
};

const COLORS = ["#10b981", "#06b6d4", "#6366f1", "#f59e0b", "#ec4899", "#8b5cf6"];

const CustomTooltip = ({ active, payload, label }: any) => {
  if (active && payload && payload.length) {
    return (
      <div style={{
        background: "rgba(18, 20, 29, 0.9)",
        border: "1px solid rgba(255, 255, 255, 0.1)",
        padding: "12px",
        borderRadius: "8px",
        boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4)",
        color: "#fff"
      }}>
        <p style={{ margin: 0, fontWeight: 700, marginBottom: "8px" }}>{label}</p>
        {payload.map((entry: any, index: number) => (
          <p key={index} style={{ margin: 0, color: entry.color, fontSize: "14px" }}>
            {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
          </p>
        ))}
      </div>
    );
  }
  return null;
};

export default function ChartComponent({ config, data }: ChartProps) {
  if (!config || !data || data.length === 0) return null;
  
  const type = config.chart_type?.toLowerCase() || "table";
  const xKey = config.x_axis;
  const yKey = config.y_axis;

  if (type === "table" || !xKey || !yKey) return null;

  return (
    <div style={{ 
      background: "var(--bg-surface)", 
      border: "1px solid var(--border-subtle)",
      borderRadius: "16px",
      padding: "24px",
      marginTop: "24px",
      boxShadow: "0 4px 20px rgba(0,0,0,0.2)"
    }}>
      {config.title && (
        <h3 style={{ marginBottom: "20px", fontSize: "18px", color: "var(--text-main)" }}>
          📊 {config.title}
        </h3>
      )}
      <div style={{ height: 350, width: "100%" }}>
        <ResponsiveContainer width="100%" height="100%">
          {type === "bar" ? (
            <BarChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey={xKey} stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)'}} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)'}} tickLine={false} axisLine={false} tickFormatter={(value) => value >= 1000 ? `${(value/1000).toFixed(0)}k` : value} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ paddingTop: "20px" }}/>
              <Bar dataKey={yKey} fill="var(--accent-emerald)" radius={[4, 4, 0, 0]} barSize={40} />
            </BarChart>
          ) : type === "line" ? (
            <LineChart data={data} margin={{ top: 10, right: 10, left: 0, bottom: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey={xKey} stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)'}} tickLine={false} axisLine={false} />
              <YAxis stroke="var(--text-muted)" tick={{fill: 'var(--text-muted)'}} tickLine={false} axisLine={false} tickFormatter={(value) => value >= 1000 ? `${(value/1000).toFixed(0)}k` : value} />
              <Tooltip content={<CustomTooltip />} />
              <Legend wrapperStyle={{ paddingTop: "20px" }}/>
              <Line type="monotone" dataKey={yKey} stroke="var(--accent-cyan)" strokeWidth={3} dot={{ r: 4, fill: "var(--bg-surface)", strokeWidth: 2 }} activeDot={{ r: 6 }} />
            </LineChart>
          ) : type === "pie" ? (
            <PieChart margin={{ top: 10, right: 10, left: 10, bottom: 10 }}>
              <Tooltip content={<CustomTooltip />} />
              <Legend />
              <Pie
                data={data}
                dataKey={yKey}
                nameKey={xKey}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                stroke="none"
              >
                {data.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
              Unsupported chart type: {type}
            </div>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
