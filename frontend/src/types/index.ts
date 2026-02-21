export interface User {
    id: string;
    email: string;
    full_name: string;
    role: string;
    is_active: boolean;
    created_at: string;
}

export interface Client {
    id: string;
    user_id: string;
    company_name: string;
    website: string | null;
    country: string;
    industry: string | null;
    monthly_budget: number;
    currency: string;
    automation_status: string;
    is_active: boolean;
    created_at: string;
}

export interface AdAccount {
    id: string;
    client_id: string;
    platform: 'meta' | 'google';
    account_id: string;
    account_name: string | null;
    status: string;
    created_at: string;
}

export interface Campaign {
    id: string;
    client_id: string;
    name: string;
    platform: string;
    objective: string | null;
    campaign_type: string | null;
    status: string;
    daily_budget: number;
    platform_campaign_id: string | null;
    created_at: string;
}

export interface MetricsSummary {
    total_spend: number;
    total_revenue: number;
    total_conversions: number;
    avg_roas: number;
    avg_cpa: number;
    avg_ctr: number;
    budget_usage_pct: number;
    monthly_budget: number;
}

export interface DailyMetricPoint {
    date: string;
    spend: number;
    revenue: number;
    conversions: number;
    roas: number;
    cpa: number;
    clicks: number;
    impressions: number;
}

export interface TopCampaign {
    campaign_id: string;
    name: string;
    platform: string;
    spend: number;
    revenue: number;
    roas: number;
    conversions: number;
    status: string;
}

export interface DashboardOverview {
    summary: MetricsSummary;
    daily_metrics: DailyMetricPoint[];
    top_campaigns: TopCampaign[];
    automation_status: string;
    recent_actions: number;
}

export interface OptimizationLog {
    id: string;
    client_id: string;
    campaign_id: string | null;
    action: string;
    reason: string | null;
    entity_type: string | null;
    old_value: string | null;
    new_value: string | null;
    status: string;
    created_at: string;
}

export interface AutomationStatus {
    automation_status: string;
    monthly_budget: number;
    country: string;
    connected_accounts: {
        meta: number;
        google: number;
    };
}

export interface BudgetSettings {
    id: string;
    client_id: string;
    monthly_cap: number;
    current_month_spend: number;
    prospecting_pct: number;
    retargeting_pct: number;
    testing_pct: number;
}
