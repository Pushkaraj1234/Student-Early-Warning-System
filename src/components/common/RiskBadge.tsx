import React from 'react';
import { RiskLevel } from '../../types.js';
import { ShieldCheck, AlertTriangle, AlertOctagon, HelpCircle } from 'lucide-react';

interface RiskBadgeProps {
  level: RiskLevel | string;
  probability?: number;
  showIcon?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  level,
  probability,
  showIcon = true,
  size = 'md',
  className = ''
}) => {
  const normLevel = (level || 'LOW').toUpperCase();

  let bg = 'bg-emerald-50 text-emerald-700 border-emerald-200';
  let icon = <ShieldCheck className="w-3.5 h-3.5 mr-1 text-emerald-600" />;
  let label = 'Low Risk';

  if (normLevel === 'CRITICAL') {
    bg = 'bg-rose-50 text-rose-700 border-rose-200';
    icon = <AlertOctagon className="w-3.5 h-3.5 mr-1 text-rose-600 animate-pulse" />;
    label = 'Critical Risk';
  } else if (normLevel === 'HIGH') {
    bg = 'bg-amber-50 text-amber-700 border-amber-300';
    icon = <AlertTriangle className="w-3.5 h-3.5 mr-1 text-amber-600" />;
    label = 'High Risk';
  } else if (normLevel === 'MODERATE') {
    bg = 'bg-yellow-50 text-yellow-800 border-yellow-200';
    icon = <AlertTriangle className="w-3.5 h-3.5 mr-1 text-yellow-600" />;
    label = 'Moderate Risk';
  }

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 font-medium border rounded-full',
    md: 'text-xs px-2.5 py-1 font-semibold border rounded-full',
    lg: 'text-sm px-3.5 py-1.5 font-bold border rounded-full'
  }[size];

  return (
    <span
      id={`risk-badge-${normLevel.toLowerCase()}`}
      className={`inline-flex items-center whitespace-nowrap transition-colors shadow-xs ${sizeClasses} ${bg} ${className}`}
    >
      {showIcon && icon}
      <span>{label}</span>
      {probability !== undefined && (
        <span className="ml-1.5 opacity-90 font-mono">
          ({probability.toFixed(1)}%)
        </span>
      )}
    </span>
  );
};
