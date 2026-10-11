import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import {
  CHART_WINDOW_DAYS,
  buildDayWindow,
  completionTrendByDay,
  focusedMinutesByDay,
  statusChartData,
} from "../utils/analytics";

// Same palette as the status badges in styles.css.
const STATUS_COLORS = {
  scheduled: "#94a3b8",
  active: "#3b5bdb",
  paused: "#f59e0b",
  completed: "#22a06b",
  interrupted: "#e8590c",
  abandoned: "#6b7280",
  overdue: "#d63939",
};
const BAR_COLOR = "#3b5bdb";
const LINE_COLOR = "#22a06b";

function ChartCard({ title, description, hasData, emptyText, children }) {
  return (
    <section className="card chart-card" aria-label={title}>
      <h2>{title}</h2>
      <p className="muted chart-description">{description}</p>
      {hasData ? (
        <div className="chart-area">{children}</div>
      ) : (
        <p className="empty-state">{emptyText}</p>
      )}
    </section>
  );
}

export default function ProductivityCharts({ sessions, summary }) {
  const statusData = useMemo(() => statusChartData(summary.status_counts), [summary]);
  const focusedData = useMemo(
    () => focusedMinutesByDay(sessions, buildDayWindow()),
    [sessions]
  );
  const trendData = useMemo(
    () => completionTrendByDay(sessions, buildDayWindow()),
    [sessions]
  );

  const windowText = `Last ${CHART_WINDOW_DAYS} days.`;

  return (
    <div className="charts-grid">
      <ChartCard
        title="Sessions by status"
        description="All sessions, grouped by their current status."
        hasData={statusData.length > 0}
        emptyText="No sessions yet."
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={statusData}
              dataKey="value"
              nameKey="name"
              innerRadius={55}
              outerRadius={90}
              paddingAngle={2}
              isAnimationActive={false}
            >
              {statusData.map((entry) => (
                <Cell key={entry.status} fill={STATUS_COLORS[entry.status]} />
              ))}
            </Pie>
            <Tooltip formatter={(value, name) => [`${value} session(s)`, name]} />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Focused time by day"
        description={`Focused minutes (paused time excluded), by the day a session started. ${windowText}`}
        hasData={focusedData.some((point) => point.minutes > 0)}
        emptyText="No focused time recorded in this period."
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={focusedData} margin={{ top: 8, right: 8, bottom: 0, left: -12 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={16} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value, _name, item) => [
                `${value} min (${item.payload.sessions} session(s))`,
                "Focused",
              ]}
            />
            <Bar dataKey="minutes" fill={BAR_COLOR} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Completion trend"
        description={`Completed ÷ finished sessions, by the day they finished. ${windowText}`}
        hasData={trendData.some((point) => point.rate !== null)}
        emptyText="No finished sessions in this period."
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={trendData} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} minTickGap={16} />
            <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(value, _name, item) => [
                `${value}% (${item.payload.completed} of ${item.payload.finished} finished)`,
                "Completion rate",
              ]}
            />
            <Line
              type="monotone"
              dataKey="rate"
              stroke={LINE_COLOR}
              strokeWidth={2}
              dot={{ r: 3 }}
              connectNulls={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  );
}