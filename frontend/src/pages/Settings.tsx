import { useState, useEffect } from 'react';
import api from '../api/client';
import { Client, BudgetSettings } from '../types';
import { useAuth } from '../contexts/AuthContext';
import { Save, PieChart } from 'lucide-react';

export default function Settings() {
    const { user } = useAuth();
    const [client, setClient] = useState<Client | null>(null);
    const [budget, setBudget] = useState<BudgetSettings | null>(null);
    const [form, setForm] = useState({
        company_name: '',
        website: '',
        industry: '',
    });
    const [allocations, setAllocations] = useState({
        prospecting_pct: 0.50,
        retargeting_pct: 0.35,
        testing_pct: 0.15,
    });
    const [message, setMessage] = useState({ type: '', text: '' });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        fetchData();
    }, []);

    const fetchData = async () => {
        try {
            const [clientRes, budgetRes] = await Promise.all([
                api.get('/clients/me'),
                api.get('/clients/me/budget'),
            ]);
            setClient(clientRes.data);
            setBudget(budgetRes.data);
            setForm({
                company_name: clientRes.data.company_name || '',
                website: clientRes.data.website || '',
                industry: clientRes.data.industry || '',
            });
            setAllocations({
                prospecting_pct: budgetRes.data.prospecting_pct,
                retargeting_pct: budgetRes.data.retargeting_pct,
                testing_pct: budgetRes.data.testing_pct,
            });
        } catch { /* no data */ }
        setLoading(false);
    };

    const saveCompany = async () => {
        try {
            await api.put('/clients/me', form);
            setMessage({ type: 'success', text: 'Company info saved!' });
            setTimeout(() => setMessage({ type: '', text: '' }), 3000);
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save' });
        }
    };

    const saveBudget = async () => {
        const total = allocations.prospecting_pct + allocations.retargeting_pct + allocations.testing_pct;
        if (Math.abs(total - 1) > 0.01) {
            setMessage({ type: 'error', text: `Allocations must sum to 100% (currently ${(total * 100).toFixed(0)}%)` });
            return;
        }
        try {
            await api.put('/clients/me/budget', allocations);
            setMessage({ type: 'success', text: 'Budget allocations saved!' });
            setTimeout(() => setMessage({ type: '', text: '' }), 3000);
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save' });
        }
    };

    if (loading) {
        return <div className="loading-spinner"><div className="spinner" /></div>;
    }

    return (
        <>
            <div className="page-header">
                <h1>Settings</h1>
                <p>Manage your company and budget allocation</p>
            </div>

            <div className="page-content">
                {message.text && (
                    <div className={`alert alert-${message.type}`}>{message.text}</div>
                )}

                <div className="setup-grid">
                    {/* Company Info */}
                    <div className="setup-section">
                        <h3>Company Information</h3>
                        <p>Update your company details</p>
                        <div className="form-group">
                            <label>Company Name</label>
                            <input
                                type="text"
                                className="form-input"
                                value={form.company_name}
                                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                            />
                        </div>
                        <div className="form-group">
                            <label>Website</label>
                            <input
                                type="url"
                                className="form-input"
                                placeholder="https://yourstore.com"
                                value={form.website}
                                onChange={(e) => setForm({ ...form, website: e.target.value })}
                            />
                        </div>
                        <div className="form-group">
                            <label>Industry</label>
                            <input
                                type="text"
                                className="form-input"
                                placeholder="e.g. Fashion, Electronics"
                                value={form.industry}
                                onChange={(e) => setForm({ ...form, industry: e.target.value })}
                            />
                        </div>
                        <button className="btn btn-primary btn-sm" onClick={saveCompany}>
                            <Save size={14} /> Save Company Info
                        </button>
                    </div>

                    {/* Budget Allocation */}
                    <div className="setup-section">
                        <h3><PieChart size={18} style={{ display: 'inline', verticalAlign: -3 }} /> Budget Allocation</h3>
                        <p>How your ad budget is distributed across campaign types</p>

                        <div className="form-group">
                            <label>Prospecting ({(allocations.prospecting_pct * 100).toFixed(0)}%)</label>
                            <input
                                type="range"
                                min="0" max="1" step="0.05"
                                value={allocations.prospecting_pct}
                                onChange={(e) => setAllocations({ ...allocations, prospecting_pct: parseFloat(e.target.value) })}
                                style={{ width: '100%' }}
                            />
                        </div>

                        <div className="form-group">
                            <label>Retargeting ({(allocations.retargeting_pct * 100).toFixed(0)}%)</label>
                            <input
                                type="range"
                                min="0" max="1" step="0.05"
                                value={allocations.retargeting_pct}
                                onChange={(e) => setAllocations({ ...allocations, retargeting_pct: parseFloat(e.target.value) })}
                                style={{ width: '100%' }}
                            />
                        </div>

                        <div className="form-group">
                            <label>Testing ({(allocations.testing_pct * 100).toFixed(0)}%)</label>
                            <input
                                type="range"
                                min="0" max="1" step="0.05"
                                value={allocations.testing_pct}
                                onChange={(e) => setAllocations({ ...allocations, testing_pct: parseFloat(e.target.value) })}
                                style={{ width: '100%' }}
                            />
                        </div>

                        <div style={{
                            fontSize: 13,
                            padding: '8px 12px',
                            borderRadius: 8,
                            background: Math.abs(allocations.prospecting_pct + allocations.retargeting_pct + allocations.testing_pct - 1) < 0.01
                                ? 'rgba(16,185,129,0.1)'
                                : 'rgba(239,68,68,0.1)',
                            color: Math.abs(allocations.prospecting_pct + allocations.retargeting_pct + allocations.testing_pct - 1) < 0.01
                                ? 'var(--accent-400)'
                                : 'var(--danger-400)',
                            marginBottom: 16,
                        }}>
                            Total: {((allocations.prospecting_pct + allocations.retargeting_pct + allocations.testing_pct) * 100).toFixed(0)}%
                            {Math.abs(allocations.prospecting_pct + allocations.retargeting_pct + allocations.testing_pct - 1) < 0.01
                                ? ' ✓' : ' (must equal 100%)'}
                        </div>

                        <button className="btn btn-primary btn-sm" onClick={saveBudget}>
                            <Save size={14} /> Save Allocations
                        </button>
                    </div>

                    {/* Account Info */}
                    <div className="setup-section" style={{ gridColumn: '1 / -1' }}>
                        <h3>Account Information</h3>
                        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20, marginTop: 16 }}>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Email</div>
                                <div style={{ fontSize: 14 }}>{user?.email}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Role</div>
                                <div style={{ fontSize: 14, textTransform: 'capitalize' }}>{user?.role}</div>
                            </div>
                            <div>
                                <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Member Since</div>
                                <div style={{ fontSize: 14 }}>
                                    {user?.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </>
    );
}
