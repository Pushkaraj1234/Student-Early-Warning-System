import React, { useState } from 'react';
import { HistoricalRiskPoint, HistoricalRiskSummary, RiskLevel } from '../../types.js';
import { TrendingDown, TrendingUp, Minus, AlertCircle, CheckCircle2, ShieldAlert } from 'lucide-react';
import { RiskBadge } from './RiskBadge.js';

interface RiskSparklineProps {
  points: HistoricalRiskPoint[];
  summary?: HistoricalRiskSummary;
  height?: number;
  width?: number | string;
  variant?: 'compact' | 'badge' | 'card';
  interactive?: boolean;
  className?: string;
}

export const RiskSparkline: React.FC<RiskSparklineProps> = ({
  points = [],
  summary,
  height = 46,
  width = '100%',
  variant = 'compact',
  interactive = true,
  className = ''
}) => {
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null);

  // If no points provided, return null or fallback
  if (!points || points.length === 0) {
    return (
      <div className="text-[11px] text-slate-400 italic py-2">
        No historical risk checkpoints recorded.
      </div>
    );
  }

  // Ensure points have valid numbers
  const validPoints = points.map((p, idx) => ({
    ...p,
    riskProbability: typeof p.riskProbability === 'number' ? Math.max(0, Math.min(100, p.riskProbability)) : 25,
    shortLabel: p.shortLabel || `W${idx * 4 + 1}`
  }));

  const startProb = validPoints[0].riskProbability;
  const endProb = validPoints[validPoints.length - 1].riskProbability;
  const netDelta = summary?.netChange ?? Math.round((endProb - startProb) * 10) / 10;
  
  // Improving = risk decreased (negative delta); Declining = risk increased (positive delta)
  const pattern = summary?.trendPattern || (netDelta <= -4 ? 'IMPROVING' : netDelta >= 4 ? 'DECLINING' : 'STABLE');

  // Color mappings
  const theme = pattern === 'IMPROVING'
    ? {
        stroke: '#10b981', // emerald-500
        strokeDark: '#059669',
        fillStart: 'rgba(16, 185, 129, 0.28)',
        fillEnd: 'rgba(16, 185, 129, 0.01)',
        badgeBg: 'bg-emerald-50 border-emerald-200 text-emerald-800',
        badgeText: 'text-emerald-700',
        icon: TrendingDown,
        label: 'Improving Pattern',
        subLabel: 'Risk Decreased'
      }
    : pattern === 'DECLINING'
    ? {
        stroke: '#f43f5e', // rose-500
        strokeDark: '#e11d48',
        fillStart: 'rgba(244, 63, 94, 0.28)',
        fillEnd: 'rgba(244, 63, 94, 0.01)',
        badgeBg: 'bg-rose-50 border-rose-200 text-rose-800',
        badgeText: 'text-rose-700',
        icon: TrendingUp,
        label: 'Risk Escalating',
        subLabel: 'Decline Pattern'
      }
    : {
        stroke: '#6366f1', // indigo-500
        strokeDark: '#4f46e5',
        fillStart: 'rgba(99, 102, 241, 0.22)',
        fillEnd: 'rgba(99, 102, 241, 0.01)',
        badgeBg: 'bg-slate-100 border-slate-200 text-slate-700',
        badgeText: 'text-slate-600',
        icon: Minus,
        label: 'Stable Pattern',
        subLabel: 'Consistent Track'
      };

  const IconComponent = theme.icon;

  // SVG Dimension & Coordinate Calculations
  const svgWidth = 240;
  const svgHeight = height;
  const paddingX = 14;
  const paddingY = 9;
  const drawingWidth = svgWidth - paddingX * 2;
  const drawingHeight = svgHeight - paddingY * 2;

  // Min and max for scaling
  const minVal = Math.max(0, Math.min(...validPoints.map(p => p.riskProbability)) - 5);
  const maxVal = Math.min(100, Math.max(...validPoints.map(p => p.riskProbability)) + 5);
  const range = maxVal - minVal || 1;

  const coords = validPoints.map((p, idx) => {
    const x = paddingX + (idx / Math.max(1, validPoints.length - 1)) * drawingWidth;
    // Lower y is higher value (SVG coordinates: 0 is top)
    const y = paddingY + drawingHeight - ((p.riskProbability - minVal) / range) * drawingHeight;
    return { x, y, point: p };
  });

  // Build SVG path
  const pathD = coords.reduce((acc, curr, idx) => {
    return idx === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`;
  }, '');

  // Build Area path (closed at bottom)
  const areaD = `${pathD} L ${coords[coords.length - 1].x} ${svgHeight} L ${coords[0].x} ${svgHeight} Z`;

  const gradientId = `sparkline-grad-${validPoints[0]?.id || Math.random().toString(36).substring(2, 8)}`;

  // Active or hovered point
  const activeIndex = hoveredIndex !== null ? hoveredIndex : validPoints.length - 1;
  const activeCoord = coords[activeIndex];

  if (variant === 'badge') {
    // Ultra compact pill sparkline for inline badges
    return (
      <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-lg border text-xs font-semibold ${theme.badgeBg} ${className}`}>
        <IconComponent className="w-3.5 h-3.5 shrink-0" />
        <span>{theme.label} ({netDelta > 0 ? `+${netDelta}%` : `${netDelta}%`})</span>
        <svg width={52} height={20} className="overflow-visible">
          <defs>
            <linearGradient id={`${gradientId}-badge`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={theme.stroke} stopOpacity="0.3" />
              <stop offset="100%" stopColor={theme.stroke} stopOpacity="0" />
            </linearGradient>
          </defs>
          <path
            d={coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${paddingX * 0.2 + (i / (validPoints.length - 1)) * 44} ${16 - ((c.point.riskProbability - minVal) / range) * 12}`).join(' ')}
            fill="none"
            stroke={theme.stroke}
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </div>
    );
  }

  return (
    <div className={`relative flex flex-col ${className}`}>
      {/* Top micro header / pattern status indicator */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-[10px] font-bold border ${theme.badgeBg}`}>
            <IconComponent className="w-3 h-3" />
            {theme.label}
          </span>
          <span className="text-[10px] text-slate-500 font-mono">
            Past Semester Trajectory
          </span>
        </div>

        <div className="text-right flex items-center gap-1">
          <span className="text-[10px] text-slate-400 font-mono">Net Δ</span>
          <span className={`text-xs font-bold font-mono ${netDelta < 0 ? 'text-emerald-700' : netDelta > 0 ? 'text-rose-700' : 'text-slate-700'}`}>
            {netDelta > 0 ? `+${netDelta}%` : `${netDelta}%`}
          </span>
        </div>
      </div>

      {/* Sparkline Canvas Area */}
      <div className="relative w-full bg-slate-50/70 border border-slate-200/80 rounded-xl p-2.5 overflow-hidden">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-auto block overflow-visible"
          style={{ maxHeight: `${height + 10}px` }}
        >
          <defs>
            <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={theme.fillStart} />
              <stop offset="100%" stopColor={theme.fillEnd} />
            </linearGradient>
            <filter id={`glow-${gradientId}`} x="-20%" y="-20%" width="140%" height="140%">
              <feDropShadow dx="0" dy="2" stdDeviation="2" floodColor={theme.stroke} floodOpacity="0.25" />
            </filter>
          </defs>

          {/* Background area fill */}
          <path d={areaD} fill={`url(#${gradientId})`} />

          {/* Reference baseline line (faint dashed) */}
          <line
            x1={paddingX}
            y1={coords[0].y}
            x2={svgWidth - paddingX}
            y2={coords[0].y}
            stroke="#cbd5e1"
            strokeDasharray="2 3"
            strokeWidth="0.8"
          />

          {/* Main sparkline trajectory stroke */}
          <path
            d={pathD}
            fill="none"
            stroke={theme.stroke}
            strokeWidth="2.4"
            strokeLinecap="round"
            strokeLinejoin="round"
            filter={`url(#glow-${gradientId})`}
          />

          {/* Checkpoint Dots */}
          {coords.map((c, i) => {
            const isHovered = hoveredIndex === i;
            const isLast = i === coords.length - 1;
            const isFirst = i === 0;

            return (
              <g
                key={i}
                className="cursor-pointer transition-transform"
                onMouseEnter={() => interactive && setHoveredIndex(i)}
                onMouseLeave={() => interactive && setHoveredIndex(null)}
              >
                {/* Invisible hit area for easier hover */}
                <circle cx={c.x} cy={c.y} r={12} fill="transparent" />

                {/* Visible dot */}
                <circle
                  cx={c.x}
                  cy={c.y}
                  r={isHovered ? 5.5 : isLast || isFirst ? 4 : 3}
                  fill={isHovered ? '#0f172a' : isLast ? theme.strokeDark : '#ffffff'}
                  stroke={theme.stroke}
                  strokeWidth={isHovered ? 2.5 : isLast ? 2 : 1.8}
                />
              </g>
            );
          })}

          {/* Highlight indicator ring on active hover */}
          {hoveredIndex !== null && activeCoord && (
            <circle
              cx={activeCoord.x}
              cy={activeCoord.y}
              r={8}
              fill="none"
              stroke={theme.stroke}
              strokeWidth="1.2"
              strokeDasharray="2 2"
              className="animate-spin"
            />
          )}
        </svg>

        {/* Checkpoint labels underneath */}
        <div className="flex items-center justify-between text-[9px] font-mono text-slate-400 mt-1 px-1">
          {validPoints.map((p, i) => (
            <button
              key={i}
              type="button"
              onClick={() => setHoveredIndex(i)}
              className={`transition-colors font-medium ${
                hoveredIndex === i ? 'text-slate-900 font-bold' : 'hover:text-slate-700'
              }`}
            >
              {p.shortLabel}
            </button>
          ))}
        </div>

        {/* Hover / Active Checkpoint Information Tooltip */}
        {activeCoord && (
          <div className="mt-2 pt-2 border-t border-slate-200/70 flex flex-wrap items-center justify-between gap-1 text-[10px]">
            <div className="flex items-center gap-1.5">
              <span className="font-bold text-slate-800">
                {activeCoord.point.checkpoint}
              </span>
              <RiskBadge level={activeCoord.point.riskLevel as RiskLevel} size="sm" showIcon={false} />
            </div>

            <div className="flex items-center gap-2">
              <span className="text-slate-500 italic max-w-[170px] truncate">
                {activeCoord.point.eventNote}
              </span>
              <span className="font-mono font-black text-slate-900 bg-white px-1.5 py-0.5 rounded border border-slate-200">
                {activeCoord.point.riskProbability}%
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
