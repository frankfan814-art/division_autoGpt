/**
 * QualityBadge component for displaying quality score
 */

import { EvaluationResult } from '@/types';

interface QualityBadgeProps {
  evaluation?: EvaluationResult;
  score?: number;  // 🔥 新增：支持直接传入分数
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
}

const sizeStyles = {
  sm: 'text-sm',
  md: 'text-base',
  lg: 'text-lg',
};

export const QualityBadge = ({ evaluation, score: directScore, size = 'md', showLabel = true }: QualityBadgeProps) => {
  // 🔥 支持直接传入分数
  if (directScore !== undefined) {
    const displayScore = Math.round(directScore * 100);
    const scoreColor = directScore >= 0.8 ? 'text-green-600' : directScore >= 0.6 ? 'text-yellow-600' : 'text-red-600';
    const bgColor = directScore >= 0.8 ? 'bg-green-100' : directScore >= 0.6 ? 'bg-yellow-100' : 'bg-red-100';

    return (
      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs font-medium ${bgColor} ${sizeStyles[size]} ${scoreColor}`}>
        {displayScore}%
      </span>
    );
  }

  if (!evaluation) return null;

  const { score, passed, quality_score, consistency_score } = evaluation;

  // 🔥 如果有分别的质量和一致性评分，分别显示
  if (quality_score !== undefined && consistency_score !== undefined) {
    const qualityColor = quality_score >= 0.8 ? 'text-green-600' : quality_score >= 0.6 ? 'text-yellow-600' : 'text-red-600';
    const consistencyColor = consistency_score >= 0.8 ? 'text-green-600' : consistency_score >= 0.6 ? 'text-yellow-600' : 'text-red-600';
    const bgColor = passed ? 'bg-green-100' : 'bg-red-100';

    return (
      <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${bgColor}`}>
        {showLabel && (
          <span className="text-gray-700 font-medium">
            {passed ? '通过' : '未通过'}
          </span>
        )}
        <span className={`${sizeStyles[size]} ${qualityColor} font-bold`}>
          📈 {(quality_score * 10).toFixed(1)}
        </span>
        <span className="text-gray-400">|</span>
        <span className={`${sizeStyles[size]} ${consistencyColor} font-bold`}>
          🔍 {(consistency_score * 10).toFixed(1)}
        </span>
      </div>
    );
  }

  // 🔥 回退到旧的单分数显示
  const displayScore = Math.round(score * 100);
  const scoreColor = score >= 0.8 ? 'text-green-600' : score >= 0.6 ? 'text-yellow-600' : 'text-red-600';
  const bgColor = score >= 0.8 ? 'bg-green-100' : score >= 0.6 ? 'bg-yellow-100' : 'bg-red-100';

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full ${bgColor}`}>
      {showLabel && (
        <span className="text-gray-700 font-medium">
          {passed ? '通过' : '未通过'}
        </span>
      )}
      <span className={`${sizeStyles[size]} ${scoreColor} font-bold`}>
        {displayScore}/100
      </span>
    </div>
  );
};
