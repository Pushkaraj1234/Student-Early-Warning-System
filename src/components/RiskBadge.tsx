import React from 'react';
import { RiskLevel, Trajectory, DataProvenance } from '../types';
import { RISK_LEVEL_CONFIG, TRAJECTORY_CONFIG } from '../utils/formatting';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, HelpCircle } from 'lucide-react';

interface RiskBadgeProps {
  level: RiskLevel;
  size?: 'sm' | 'md' | 'lg';
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md' }) => {
  const config = RISK_LEVEL_CONFIG[level] || RISK_LEVEL_CONFIG.stable;
  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm font-medium',
    lg: 'px-3.5 py-1.5 text-base font-semibold',
  };

  return (
    <span
      className={`inline-flex items-center rounded-full border ${config.badgeClass} ${sizeClasses[size]}`}
    >
      <span
        className={`w-2 h-2 rounded-full mr-1.5 ${
          level === 'high'
            ? 'bg-rose-500 animate-pulse'
            : level === 'elevated'
            ? 'bg-orange-500'
            : level === 'watch'
            ? 'bg-amber-500'
            : 'bg-emerald-500'
        }`}
      />
      {config.label}
    </span>
  );
};

interface TrajectoryBadgeProps {
  trajectory: Trajectory;
  forStaff?: boolean;
}

export const TrajectoryBadge: React.FC<TrajectoryBadgeProps> = ({
  trajectory,
  forStaff = false,
}) => {
  const config = TRAJECTORY_CONFIG[trajectory] || TRAJECTORY_CONFIG.insufficient_history;
  const label = forStaff ? config.staffLabel : config.studentLabel;

  const getIcon = () => {
    switch (trajectory) {
      case 'rapidly_increasing':
        return <AlertTriangle className="w-4 h-4 mr-1 text-rose-600" />;
      case 'increasing':
        return <TrendingUp className="w-4 h-4 mr-1 text-amber-600" />;
      case 'improving':
        return <TrendingDown className="w-4 h-4 mr-1 text-emerald-600" />;
      case 'stable':
        return <Minus className="w-4 h-4 mr-1 text-blue-600" />;
      default:
        return <HelpCircle className="w-4 h-4 mr-1 text-slate-400" />;
    }
  };

  return (
    <span className="inline-flex items-center text-xs sm:text-sm font-medium text-slate-700 bg-slate-100 px-2.5 py-1 rounded-md border border-slate-200">
      {getIcon()}
      {label}
    </span>
  );
};

export const ProvenanceBadge: React.FC<{ provenance: DataProvenance }> = ({ provenance }) => {
  const colors = {
    synthetic: 'bg-purple-100 text-purple-800 border-purple-200',
    institutional: 'bg-blue-100 text-blue-800 border-blue-200',
    benchmark: 'bg-slate-100 text-slate-800 border-slate-200',
  };

  return (
    <span
      className={`inline-flex items-center text-xs font-mono uppercase tracking-wider px-2 py-0.5 rounded border ${colors[provenance]}`}
    >
      {provenance}
    </span>
  );
};
