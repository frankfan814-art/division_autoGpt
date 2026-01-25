/**
 * QualityBadge component for displaying quality score
 */

import { EvaluationResult } from '@/types';

interface QualityBadgeProps {
  evaluation?: EvaluationResult;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const sizeStyles = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
};

export const QualityBadge = ({ evaluation, size = 'md', showLabel = true }: QualityBadgeProps) => {
  if (!evaluation) return null;

  const { score, passed } = evaluation;
  const scoreColor = score >= 80 ? 'text-green-600' : score >= 60 ? 'text-yellow-600' : 'text-red-600';
  const bgColor = score >= 80 ? 'bg-green-100' : score >= 60 ? 'bg-yellow-100' : 'bg-red-100';

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${bgColor}`}>
      {showLabel && (
        <span className="text-gray-700 font-medium">
          {passed ? '通过' : '未通过'}
        </span>
      )}
      <span className={`${sizeStyles[size]} ${scoreColor} font-bold`}>
        {score}/100
      </span>
    </div>
  );
};
