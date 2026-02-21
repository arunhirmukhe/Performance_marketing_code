import { useState, useEffect } from 'react';
import api from '../api/client';
import { Campaign, OptimizationLog } from '../types';
import {
    TrendingUp, TrendingDown, Pause, Play, BarChart3,
    ArrowUpRight, ArrowDownRight, Clock
} from 'lucide-react';

export default function CampaignInsights() {
    const [campaigns, setCampaigns] = useState<Campaign[]>([]);
    const [logs, setLogs] = useState<OptimizationLog[]>([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState<'campaigns' | 'logs'>('campaigns');

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [campaignsRes, logsRes] = await Promise.all([
                api.get('/campaigns'),
                api.get('/automation/logs?limit=30'),
            ]);
            setCampaigns(campaignsRes.data.campaigns || []);
            setLogs(logsRes.data || []);
        } catch {
            // No data
        } finally {
            setLoading(false);
        }
    };

    const pauseAutomation = async () => {
        try {
            await api.post('/automation/pause');
            fetchData();
        } catch { /* handled */ }
    };

    const resumeAutomation = async () => {
        try {
            await api.post('/automation/resume');
            fetchData();
        } catch { /* handled */ }
    };

    const getActionIcon = (action: string) => {
        switch (action) {
            case 'budget_increase': return <ArrowUpRight size={14} />;
            case 'budget_decrease': return <ArrowDownRight size={14} />;
            case 'campaign_paused': return <Pause size={14} />;
            case 'campaign_created': return <Play size={14} />;
            default: return <BarChart3 size={14} />;
        }
    };

    const getActionColor = (action: string) => {
        if (action.includes('increase') || action === 'campaign_created' || action === 'automation_deploy') return 'var(--accent-400)';
        if (action.includes('decrease') || action.includes('pause')) return 'var(--warn-400)';
        if (action.includes('failed') || action.includes('error')) return 'var(--danger-400)';
        return 'var(--primary-400)';
    };

    if (loading) {
        return <div className="loading-spinner"><div className="spinner" /></div>;
    }

    return (
        <>
            <div className="page-header">
                <h1>Campaign Insights</h1>
                <p>Monitor campaigns and view automation actions</p>
            </div>

            <div className="page-content">
                {/* Controls */}
                <div className="automation-controls">
                    <div className="automation-status">
                        <BarChart3 size={20} style={{ color: 'var(--primary-400)' }} />
                        <span style={{ fontWeight: 600 }}>{campaigns.length} Campaigns</span>
                        <span style={{ color: 'var(--text-muted)', fontSize: 13 }}>
                            · {campaigns.filter(c => c.status === 'active').length} active
                        </span>
                    </div>
                    <button className="btn btn-secondary btn-sm" onClick={pauseAutomation}>
                        <Pause size={14} /> Pause All
                    </button>
                    <button className="btn btn-accent btn-sm" onClick={resumeAutomation}>
                        <Play size={14} /> Resume
                    </button>
                </div>

                {/* Tabs */}
                <div style={{ display: 'flex', gap: 0, marginBottom: 24 }}>
                    <button
                        className={`btn btn-sm ${activeTab === 'campaigns' ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setActiveTab('campaigns')}
                        style={{ borderRadius: '8px 0 0 8px' }}
                    >
                        Campaigns
                    </button>
                    <button
                        className={`btn btn-sm ${activeTab === 'logs' ? 'btn-primary' : 'btn-secondary'}`}
                        onClick={() => setActiveTab('logs')}
                        style={{ borderRadius: '0 8px 8px 0' }}
                    >
                        Optimization Logs ({logs.length})
                    </button>
                </div>

                {activeTab === 'campaigns' ? (
                    <div className="card">
                        {campaigns.length > 0 ? (
                            <table className="data-table">
                                <thead>
                                    <tr>
                                        <th>Campaign Name</th>
                                        <th>Platform</th>
                                        <th>Type</th>
                                        <th>Daily Budget</th>
                                        <th>Status</th>
                                        <th>Created</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {campaigns.map((c) => (
                                        <tr key={c.id}>
                                            <td style={{ fontWeight: 500 }}>{c.name}</td>
                                            <td><span className={`badge badge-${c.platform}`}>{c.platform}</span></td>
                                            <td style={{ color: 'var(--text-secondary)' }}>{c.campaign_type || '-'}</td>
                                            <td>${c.daily_budget.toFixed(2)}</td>
                                            <td><span className={`badge badge-${c.status}`}>{c.status}</span></td>
                                            <td style={{ color: 'var(--text-muted)', fontSize: 12 }}>
                                                {new Date(c.created_at).toLocaleDateString()}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        ) : (
                            <div className="empty-state">
                                <h3>No campaigns yet</h3>
                                <p>Deploy automation from Account Setup to create campaigns automatically.</p>
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="card">
                        {logs.length > 0 ? (
                            logs.map((log) => (
                                <div key={log.id} className="log-entry">
                                    <div
                                        className="log-icon"
                                        style={{ background: `${getActionColor(log.action)}15`, color: getActionColor(log.action) }}
                                    >
                                        {getActionIcon(log.action)}
                                    </div>
                                    <div className="log-content">
                                        <div className="log-action" style={{ color: getActionColor(log.action) }}>
                                            {log.action.replace(/_/g, ' ').toUpperCase()}
                                        </div>
                                        <div className="log-reason">{log.reason}</div>
                                        {log.old_value && log.new_value && (
                                            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 2 }}>
                                                {log.old_value} → {log.new_value}
                                            </div>
                                        )}
                                        <div className="log-time">
                                            <Clock size={10} style={{ verticalAlign: -1, marginRight: 4 }} />
                                            {new Date(log.created_at).toLocaleString()}
                                        </div>
                                    </div>
                                    <span className={`badge badge-${log.status === 'completed' ? 'active' : log.status === 'failed' ? 'error' : 'paused'}`}>
                                        {log.status}
                                    </span>
                                </div>
                            ))
                        ) : (
                            <div className="empty-state">
                                <h3>No optimization logs yet</h3>
                                <p>Actions taken by the automation engine will appear here.</p>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </>
    );
}
