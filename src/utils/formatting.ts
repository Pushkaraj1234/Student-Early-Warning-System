import { RiskLevel, Trajectory, RiskFactor, FactorDirection } from '../types';

export const RISK_LEVEL_CONFIG: Record<
  RiskLevel,
  { label: string; badgeClass: string; textClass: string; bgClass: string; borderClass: string }
> = {
  stable: {
    label: 'Stable',
    badgeClass: 'bg-emerald-100 text-emerald-800 border-emerald-300',
    textClass: 'text-emerald-700',
    bgClass: 'bg-emerald-50',
    borderClass: 'border-emerald-200',
  },
  watch: {
    label: 'Watch',
    badgeClass: 'bg-amber-100 text-amber-800 border-amber-300',
    textClass: 'text-amber-700',
    bgClass: 'bg-amber-50',
    borderClass: 'border-amber-200',
  },
  elevated: {
    label: 'Elevated',
    badgeClass: 'bg-orange-100 text-orange-800 border-orange-300',
    textClass: 'text-orange-700',
    bgClass: 'bg-orange-50',
    borderClass: 'border-orange-200',
  },
  high: {
    label: 'High',
    badgeClass: 'bg-rose-100 text-rose-800 border-rose-300',
    textClass: 'text-rose-700',
    bgClass: 'bg-rose-50',
    borderClass: 'border-rose-200',
  },
};

export const TRAJECTORY_CONFIG: Record<
  Trajectory,
  { studentLabel: string; staffLabel: string; icon: string; color: string }
> = {
  insufficient_history: {
    studentLabel: 'Not enough history yet',
    staffLabel: 'Not enough history',
    icon: 'help',
    color: 'text-slate-500',
  },
  improving: {
    studentLabel: 'Improving',
    staffLabel: 'Improving',
    icon: 'trending-down',
    color: 'text-emerald-600',
  },
  stable: {
    studentLabel: 'Steady',
    staffLabel: 'Stable',
    icon: 'minus',
    color: 'text-blue-600',
  },
  increasing: {
    studentLabel: 'Worth a look',
    staffLabel: 'Increasing',
    icon: 'trending-up',
    color: 'text-amber-600',
  },
  rapidly_increasing: {
    studentLabel: 'Worth a look soon',
    staffLabel: 'Rapidly increasing',
    icon: 'alert-triangle',
    color: 'text-rose-600',
  },
};

export const FEATURE_LABELS: Record<string, { label: string; format: 'percent' | 'count' | 'days' | 'score' | 'gpa' | 'raw' }> = {
  attendance_rate_to_date: { label: 'Attendance so far this term', format: 'percent' },
  attendance_rate_last_14d: { label: 'Attendance in the last 14 days', format: 'percent' },
  attendance_rate_last_7d: { label: 'Attendance in the last 7 days', format: 'percent' },
  attendance_rate_last_30d: { label: 'Attendance in the last 30 days', format: 'percent' },
  attendance_trend: { label: 'Change in weekly attendance', format: 'raw' },
  consecutive_absences: { label: 'Consecutive absences', format: 'count' },
  missed_submission_rate: { label: 'Assignments not submitted', format: 'percent' },
  mean_released_score_pct: { label: 'Average released score', format: 'score' },
  weighted_score_to_date: { label: 'Weighted score so far', format: 'score' },
  engagement_active_days_14d: { label: 'Active learning days in last 14 days', format: 'count' },
  engagement_trend: { label: 'Change in learning activity', format: 'raw' },
  prior_term_gpa: { label: 'Previous semester GPA', format: 'gpa' },
  late_submission_rate: { label: 'Submissions made after the due date', format: 'percent' },
  days_since_last_engagement: { label: 'Days since last learning activity', format: 'days' },
};

export function formatFeatureValue(factor: RiskFactor): string {
  if (factor.featureValue === null || factor.featureValue === undefined) {
    return 'Not available';
  }
  const config = FEATURE_LABELS[factor.feature] || { label: factor.feature, format: 'raw' };
  switch (config.format) {
    case 'percent':
      return `${Math.round(factor.featureValue * 100)}%`;
    case 'count':
      return `${Math.round(factor.featureValue)}`;
    case 'days':
      return `${Math.round(factor.featureValue)} days`;
    case 'score':
      return `${factor.featureValue.toFixed(1)}%`;
    case 'gpa':
      return factor.featureValue.toFixed(2);
    case 'raw':
    default:
      return `${factor.featureValue}`;
  }
}

export function getFeatureDisplayTitle(feature: string): string {
  return FEATURE_LABELS[feature]?.label || feature.replace(/_/g, ' ');
}

export function formatDirectionText(direction: FactorDirection): string {
  return direction === 'increases_risk'
    ? 'Raised the risk estimate'
    : 'Lowered the risk estimate';
}

export function formatDate(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  } catch {
    return isoString;
  }
}

export function formatTimeAgo(isoString: string): string {
  try {
    const d = new Date(isoString);
    const diffHours = Math.round((Date.now() - d.getTime()) / (1000 * 60 * 60));
    if (diffHours < 1) return 'Just now';
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.round(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return isoString;
  }
}
