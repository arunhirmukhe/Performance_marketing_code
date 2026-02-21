import { useState, useEffect } from 'react';
import api from '../api/client';
import { DashboardOverview } from '../types';
import {
    DollarSign, TrendingUp, Target, MousePointerClick,
    BarChart3, Wallet
} from 'lucide-react';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis,
    CartesianGrid, Tooltip, ResponsiveContainer, Area, AreaChart
} from 'recharts';

export default function Dashboard() {
    const [data, setData] = useState<DashboardOverview | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchDashboard();
    }, []);

    const fetchDashboard = async () => {
        try {
            const res = await api.get('/dashboard/overview');
            setData(res.data);
        } catch {
            // Empty state - no data yet
            setData(null);
        } finally {
            setLoading(false);
        }
    };

    if (loading) {
        return <div className="loading-spinner"><div className="spinner" /></div>;
    }

    const summary = data?.summary || {
        total_spend: 0, total_revenue: 0, total_conversions: 0,
        avg_roas: 0, avg_cpa: 0, avg_ctr: 0,
        budget_usage_pct: 0, monthly_budget: 0,
    };

    const formatCurrency = (val: number) =>
        val >= 1000 ? `$${(val / 1000).toFixed(1)}k` : `$${val.toFixed(2)}`;

    return (
        <>
            <div className="page-header">
                <h1>Performance Dashboard</h1>
                <p>Your real-time advertising performance overview</p>
            </div>

            <div className="page-content">
                {/* Automation Status Bar */}
                <div className="automation-controls">
                    <div className="automation-status">
                        <div className={`status-dot ${data?.automation_status || 'inactive'}`} />
                        <div>
                            <strong style={{ fontSize: 14 }}>
                                Automation: {(data?.automation_status || 'inactive').toUpperCase()}
                            </strong>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                                {data?.recent_actions || 0} actions taken this month
                            </div>
                        </div>
                    </div>
                </div>

                {/* Metric Cards */}
                <div className="metrics-grid">
                    <div className="metric-card primary">
                        <div className="metric-icon primary"><DollarSign size={20} /></div>
                        <div className="metric-label">Total Spend</div>
                        <div className="metric-value">{formatCurrency(summary.total_spend)}</div>
                    </div>
                    <div className="metric-card accent">
                        <div className="metric-icon accent"><TrendingUp size={20} /></div>
                        <div className="metric-label">Revenue</div>
                        <div className="metric-value">{formatCurrency(summary.total_revenue)}</div>
                    </div>
                    <div className="metric-card warm">
                        <div className="metric-icon warm"><BarChart3 size={20} /></div>
                        <div className="metric-label">ROAS</div>
                        <div className="metric-value">{summary.avg_roas.toFixed(2)}x</div>
                    </div>
                    <div className="metric-card primary">
                        <div className="metric-icon primary"><Target size={20} /></div>
                        <div className="metric-label">CPA</div>
                        <div className="metric-value">{formatCurrency(summary.avg_cpa)}</div>
                    </div>
                    <div className="metric-card accent">
                        <div className="metric-icon accent"><MousePointerClick size={20} /></div>
                        <div className="metric-label">Conversions</div>
                        <div className="metric-value">{summary.total_conversions.toLocaleString()}</div>
                    </div>
                    <div className="metric-card warm">
                        <div className="metric-icon warm"><Wallet size={20} /></div>
                        <div className="metric-label">Budget Usage</div>
                        <div className="metric-value">{summary.budget_usage_pct.toFixed(0)}%</div>
                    </div>
                </div>

                {/* Charts */}
                <div className="charts-grid">
                    <div className="chart-container">
                        <h3>Spend vs Revenue</h3>
                        <ResponsiveContainer width="100%" height={280}>
                            <AreaChart data={data?.daily_metrics || []}>
                                <defs>
                                    <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="revenueGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                                <XAxis
                                    dataKey="date"
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    tickFormatter={(v) => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                                />
                                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                                <Tooltip
                                    contentStyle={{
                                        background: '#1e293b', border: '1px solid rgba(148,163,184,0.12)',
                                        borderRadius: 8, boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
                                    }}
                                    labelStyle={{ color: '#f1f5f9' }}
                                />
                                <Area type="monotone" dataKey="spend" stroke="#6366f1" fill="url(#spendGrad)" name="Spend" />
                                <Area type="monotone" dataKey="revenue" stroke="#10b981" fill="url(#revenueGrad)" name="Revenue" />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="chart-container">
                        <h3>ROAS Trend</h3>
                        <ResponsiveContainer width="100%" height={280}>
                            <LineChart data={data?.daily_metrics || []}>
                                <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.08)" />
                                <XAxis
                                    dataKey="date"
                                    tick={{ fill: '#64748b', fontSize: 11 }}
                                    tickFormatter={(v) => new Date(v).toLocaleDateString('en', { month: 'short', day: 'numeric' })}
                                />
                                <YAxis tick={{ fill: '#64748b', fontSize: 11 }} />
                                <Tooltip
                                    contentStyle={{
                                        background: '#1e293b', border: '1px solid rgba(148,163,184,0.12)',
                                        borderRadius: 8,
                                    }}
                                />
                                <Line
                                    type="monotone" dataKey="roas" stroke="#f59e0b"
                                    strokeWidth={2} dot={false} name="ROAS"
                                />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </div>

                {/* Top Campaigns Table */}
                <div className="card">
                    <div className="card-header">
                        <span className="card-title">Top Performing Campaigns</span>
                    </div>
                    {(data?.top_campaigns || []).length > 0 ? (
                        <table className="data-table">
                            <thead>
                                <tr>
                                    <th>Campaign</th>
                                    <th>Platform</th>
                                    <th>Spend</th>
                                    <th>Revenue</th>
                                    <th>ROAS</th>
                                    <th>Conversions</th>
                                    <th>Status</th>
                                </tr>
                            </thead>
                            <tbody>
                                {(data?.top_campaigns || []).map((c) => (
                                    <tr key={c.campaign_id}>
                                        <td style={{ fontWeight: 500 }}>{c.name}</td>
                                        <td><span className={`badge badge-${c.platform}`}>{c.platform}</span></td>
                                        <td>{formatCurrency(c.spend)}</td>
                                        <td>{formatCurrency(c.revenue)}</td>
                                        <td style={{ fontWeight: 600, color: c.roas >= 3 ? 'var(--accent-400)' : c.roas >= 1 ? 'var(--warn-400)' : 'var(--danger-400)' }}>
                                            {c.roas.toFixed(2)}x
                                        </td>
                                        <td>{c.conversions}</td>
                                        <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    ) : (
                        <div className="empty-state">
                            <h3>No campaign data yet</h3>
                            <p>Connect your ad accounts and deploy automation to see performance data.</p>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}
