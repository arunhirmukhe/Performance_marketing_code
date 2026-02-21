import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api/client';
import { Client, AdAccount, AutomationStatus as AutoStatus } from '../types';
import {
    Facebook, Globe, DollarSign, MapPin,
    Rocket, CheckCircle, AlertCircle, Zap
} from 'lucide-react';

const COUNTRIES = [
    'US', 'UK', 'CA', 'AU', 'DE', 'FR', 'IN', 'BR', 'JP', 'KR',
    'SG', 'AE', 'SA', 'NL', 'ES', 'IT', 'SE', 'NO', 'MX', 'PH',
];

export default function AccountSetup() {
    const [searchParams] = useSearchParams();
    const [client, setClient] = useState<Client | null>(null);
    const [accounts, setAccounts] = useState<AdAccount[]>([]);
    const [automationStatus, setAutomationStatus] = useState<AutoStatus | null>(null);
    const [budget, setBudget] = useState('');
    const [country, setCountry] = useState('US');
    const [loading, setLoading] = useState(true);
    const [deploying, setDeploying] = useState(false);
    const [message, setMessage] = useState({ type: '', text: '' });

    // Credential States
    const [metaAppId, setMetaAppId] = useState('');
    const [metaAppSecret, setMetaAppSecret] = useState('');
    const [googleClientId, setGoogleClientId] = useState('');
    const [googleClientSecret, setGoogleClientSecret] = useState('');
    const [googleDevToken, setGoogleDevToken] = useState('');
    const [ga4Id, setGa4Id] = useState('');

    useEffect(() => {
        fetchData();
        // Check for OAuth callback params
        const metaParam = searchParams.get('meta');
        const googleParam = searchParams.get('google');
        if (metaParam === 'connected') setMessage({ type: 'success', text: 'Meta Ads connected successfully!' });
        if (googleParam === 'connected') setMessage({ type: 'success', text: 'Google Ads connected successfully!' });
        if (metaParam === 'error' || googleParam === 'error') {
            setMessage({ type: 'error', text: `Connection failed: ${searchParams.get('msg') || 'Unknown error'}` });
        }
    }, [searchParams]);

    const fetchData = async () => {
        try {
            const [clientRes, accountsRes, statusRes] = await Promise.all([
                api.get('/clients/me'),
                api.get('/ad-accounts'),
                api.get('/automation/status'),
            ]);
            const d = clientRes.data;
            setClient(d);
            setAccounts(accountsRes.data);
            setAutomationStatus(statusRes.data);
            setBudget(String(d.monthly_budget || ''));
            setCountry(d.country || 'US');
            setMetaAppId(d.meta_app_id || '');
            setMetaAppSecret(d.meta_app_secret || '');
            setGoogleClientId(d.google_client_id || '');
            setGoogleClientSecret(d.google_client_secret || '');
            setGoogleDevToken(d.google_developer_token || '');
            setGa4Id(d.ga4_property_id || '');
        } catch {
            // New user, no client yet
        } finally {
            setLoading(false);
        }
    };

    const connectMeta = async () => {
        try {
            const res = await api.get('/ad-accounts/meta/connect');
            window.location.href = res.data.auth_url;
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to start Meta connection. Did you save your App ID?' });
        }
    };

    const connectGoogle = async () => {
        try {
            const res = await api.get('/ad-accounts/google/connect');
            window.location.href = res.data.auth_url;
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to start Google connection. Did you save your Client ID?' });
        }
    };

    const saveSettings = async () => {
        try {
            await api.put('/clients/me', {
                monthly_budget: parseFloat(budget) || 0,
                country,
                meta_app_id: metaAppId,
                meta_app_secret: metaAppSecret,
                google_client_id: googleClientId,
                google_client_secret: googleClientSecret,
                google_developer_token: googleDevToken,
                ga4_property_id: ga4Id,
            });
            setMessage({ type: 'success', text: 'Settings saved!' });
            setTimeout(() => setMessage({ type: '', text: '' }), 3000);
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Failed to save settings' });
        }
    };

    const deployAutomation = async () => {
        setDeploying(true);
        try {
            await api.post('/automation/deploy');
            setMessage({ type: 'success', text: 'Automation deployed successfully! 🚀' });
            fetchData();
        } catch (err: any) {
            setMessage({ type: 'error', text: err.response?.data?.detail || 'Deployment failed' });
        } finally {
            setDeploying(false);
        }
    };

    const metaConnected = accounts.some(a => a.platform === 'meta' && a.status === 'connected');
    const googleConnected = accounts.some(a => a.platform === 'google' && a.status === 'connected');
    const canDeploy = (metaConnected || googleConnected) && parseFloat(budget) > 0;

    if (loading) {
        return <div className="loading-spinner"><div className="spinner" /></div>;
    }

    return (
        <>
            <div className="page-header">
                <h1>Account Setup</h1>
                <p>Connect your ad platforms and configure automation</p>
            </div>

            <div className="page-content">
                {message.text && (
                    <div className={`alert alert-${message.type}`}>{message.text}</div>
                )}

                <div className="setup-grid">
                    {/* Meta Credentials */}
                    <div className="setup-section full-width">
                        <h3>Meta Platform Credentials</h3>
                        <p>Enter your Meta App ID and Secret from developers.facebook.com</p>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Meta App ID</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={metaAppId}
                                    onChange={(e) => setMetaAppId(e.target.value)}
                                    placeholder="e.g. 123456789012345"
                                />
                            </div>
                            <div className="form-group">
                                <label>Meta App Secret</label>
                                <input
                                    type="password"
                                    className="form-input"
                                    value={metaAppSecret}
                                    onChange={(e) => setMetaAppSecret(e.target.value)}
                                    placeholder="••••••••••••••••"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Google Credentials */}
                    <div className="setup-section full-width">
                        <h3>Google Ads Credentials</h3>
                        <p>Enter your Google Cloud Client ID/Secret and Ads Developer Token</p>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Google Client ID</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={googleClientId}
                                    onChange={(e) => setGoogleClientId(e.target.value)}
                                    placeholder="xxx.apps.googleusercontent.com"
                                />
                            </div>
                            <div className="form-group">
                                <label>Google Client Secret</label>
                                <input
                                    type="password"
                                    className="form-input"
                                    value={googleClientSecret}
                                    onChange={(e) => setGoogleClientSecret(e.target.value)}
                                    placeholder="••••••••••••••••"
                                />
                            </div>
                        </div>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Developer Token</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={googleDevToken}
                                    onChange={(e) => setGoogleDevToken(e.target.value)}
                                    placeholder="Your Dev Token"
                                />
                            </div>
                            <div className="form-group">
                                <label>GA4 Property ID</label>
                                <input
                                    type="text"
                                    className="form-input"
                                    value={ga4Id}
                                    onChange={(e) => setGa4Id(e.target.value)}
                                    placeholder="e.g. 123456789"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Meta Ads Connection */}
                    <div className="setup-section">
                        <h3>Meta Ads Connection</h3>
                        <button
                            className={`connect-btn ${metaConnected ? 'connected' : ''}`}
                            onClick={connectMeta}
                        >
                            <Facebook size={20} style={{ color: '#1877f2' }} />
                            <span style={{ flex: 1, textAlign: 'left' }}>
                                {metaConnected ? 'Connected' : 'Authorize Meta Ads'}
                            </span>
                            {metaConnected ? <CheckCircle size={18} style={{ color: 'var(--accent-400)' }} /> : null}
                        </button>
                    </div>

                    {/* Google Ads Connection */}
                    <div className="setup-section">
                        <h3>Google Ads Connection</h3>
                        <button
                            className={`connect-btn ${googleConnected ? 'connected' : ''}`}
                            onClick={connectGoogle}
                        >
                            <Globe size={20} style={{ color: '#4285f4' }} />
                            <span style={{ flex: 1, textAlign: 'left' }}>
                                {googleConnected ? 'Connected' : 'Authorize Google Ads'}
                            </span>
                            {googleConnected ? <CheckCircle size={18} style={{ color: 'var(--accent-400)' }} /> : null}
                        </button>
                    </div>

                    {/* Budget & Save */}
                    <div className="setup-section">
                        <h3><DollarSign size={18} style={{ display: 'inline', verticalAlign: -3 }} /> Budget & Region</h3>
                        <div className="form-row">
                            <div className="form-group">
                                <label>Monthly Budget</label>
                                <input
                                    type="number"
                                    className="form-input"
                                    value={budget}
                                    onChange={(e) => setBudget(e.target.value)}
                                    min={0}
                                />
                            </div>
                            <div className="form-group">
                                <label>Country</label>
                                <select
                                    className="form-input"
                                    value={country}
                                    onChange={(e) => setCountry(e.target.value)}
                                >
                                    {COUNTRIES.map(c => <option key={c} value={c}>{c}</option>)}
                                </select>
                            </div>
                        </div>
                        <button className="btn btn-secondary w-full mt-4" onClick={saveSettings}>
                            Save All Settings
                        </button>
                    </div>

                    {/* Deploy */}
                    <div className="deploy-section">
                        <Zap size={32} style={{ color: 'var(--primary-400)', marginBottom: 8 }} />
                        <h3>Ready to Launch?</h3>
                        <p style={{ fontSize: 13, opacity: 0.8, marginBottom: 16 }}>
                            {canDeploy
                                ? 'Credentials saved and platforms authorized. Launch automation now.'
                                : 'Save credentials, authorize platforms, and set a budget to launch.'}
                        </p>
                        <button
                            className="btn btn-primary w-full"
                            onClick={deployAutomation}
                            disabled={!canDeploy || deploying}
                        >
                            <Rocket size={18} />
                            {deploying ? 'Deploying...' : 'Deploy Automation'}
                        </button>
                    </div>
                </div>
            </div>

            <style>{`
                .full-width { grid-column: 1 / -1; }
                .form-row { display: flex; gap: 16px; margin-bottom: 12px; }
                .form-group { flex: 1; display: flex; flex-direction: column; gap: 4px; }
                .form-group label { font-size: 12px; color: var(--text-muted); font-weight: 500; }
                .w-full { width: 100%; }
                .mt-4 { margin-top: 16px; }
                .setup-section h3 { margin-bottom: 8px; font-size: 16px; }
                .setup-section p { margin-bottom: 16px; font-size: 13px; color: var(--text-muted); }
            `}</style>
        </>
    );
}
