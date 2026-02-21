import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
    LayoutDashboard, Settings as SettingsIcon, Zap,
    BarChart3, LogOut, Rocket
} from 'lucide-react';

export default function Layout() {
    const { user, logout } = useAuth();

    const initials = user?.full_name
        ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
        : '?';

    return (
        <div className="app-layout">
            {/* Sidebar */}
            <aside className="sidebar">
                <div className="sidebar-logo">
                    <h2>FAGE</h2>
                    <span>Growth Engine</span>
                </div>

                <nav className="sidebar-nav">
                    <NavLink to="/dashboard" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        <LayoutDashboard size={18} />
                        Dashboard
                    </NavLink>

                    <NavLink to="/setup" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        <Rocket size={18} />
                        Account Setup
                    </NavLink>

                    <NavLink to="/campaigns" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        <BarChart3 size={18} />
                        Campaign Insights
                    </NavLink>

                    <NavLink to="/settings" className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
                        <SettingsIcon size={18} />
                        Settings
                    </NavLink>
                </nav>

                <div className="sidebar-footer">
                    <div className="sidebar-user">
                        <div className="sidebar-user-avatar">{initials}</div>
                        <div className="sidebar-user-info">
                            <div className="sidebar-user-name">{user?.full_name}</div>
                            <div className="sidebar-user-email">{user?.email}</div>
                        </div>
                    </div>
                    <button className="btn btn-secondary btn-sm btn-full" onClick={logout} style={{ marginTop: 12 }}>
                        <LogOut size={14} /> Sign Out
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main className="main-content">
                <Outlet />
            </main>
        </div>
    );
}
