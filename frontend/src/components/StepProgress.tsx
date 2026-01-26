/**
 * StepProgress component - 显示详细的步骤级进度（含历史）
 */

import { useTaskStore } from '@/stores/taskStore';
import { StepProgress as StepProgressType } from '@/stores/taskStore';
import styles from './StepProgress.module.css';

export const StepProgress = () => {
  const stepProgress = useTaskStore((state) => state.stepProgress);
  const stepHistory = useTaskStore((state) => state.stepHistory);

  // 没有任何步骤时
  if (!stepProgress && stepHistory.length === 0) {
    return null;
  }

  return (
    <div className={styles['step-progress']}>
      {/* 显示最近的历史记录（最多5条） */}
      {stepHistory.slice(0, 5).map((step, index) => (
        <div key={step.timestamp || index} className={styles['step-item']}>
          {renderStep(step, index === 0)}
        </div>
      ))}
    </div>
  );
};

function renderStep(step: StepProgressType, isLatest: boolean = false) {
  // 根据是否为最新步骤添加样式
  const containerClass = isLatest ? styles['step-latest'] : styles['step-history'];

  switch (step.step) {
    case 'context_retrieval':
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-icon']}>🔍</span>
          <span className={styles['step-message']}>{step.message}</span>
        </div>
      );

    case 'context_retrieval_complete':
      return (
        <div className={`${styles.step} ${styles['step-success']} ${containerClass}`}>
          <span className={styles['step-icon']}>✅</span>
          <span className={styles['step-message']}>
            {step.message}
            {step.context_types && step.context_types.length > 0 && (
              <span className={styles['step-detail']}>
                (类型: {step.context_types.slice(0, 3).join(', ')})
              </span>
            )}
          </span>
        </div>
      );

    case 'building_prompt':
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-icon']}>📝</span>
          <span className={styles['step-message']}>{step.message}</span>
        </div>
      );

    case 'llm_call_start':
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-icon']}>🤖</span>
          <span className={styles['step-message']}>{step.message}</span>
          {step.llm_provider && (
            <span className={styles['step-detail']}>
              ({getProviderName(step.llm_provider)})
            </span>
          )}
        </div>
      );

    case 'llm_call_complete':
      return (
        <div className={`${styles.step} ${styles['step-success']} ${containerClass}`}>
          <span className={styles['step-icon']}>✅</span>
          <span className={styles['step-message']}>
            {step.message}
            {step.tokens_used && (
              <span className={styles['step-detail']}>
                ({step.tokens_used.toLocaleString()} tokens, {step.content_length?.toLocaleString()} 字符)
              </span>
            )}
          </span>
        </div>
      );

    case 'evaluation_start':
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-icon']}>📊</span>
          <span className={styles['step-message']}>{step.message}</span>
        </div>
      );

    case 'evaluation_complete':
      const qualityPassed = step.quality_score !== undefined && step.quality_score >= 0.8;
      const consistencyPassed = step.consistency_score !== undefined && step.consistency_score >= 0.8;

      return (
        <div className={`${styles.step} ${step.passed ? styles['step-success'] : styles['step-warning']} ${containerClass}`}>
          <span className={styles['step-icon']}>{step.passed ? '✅' : '⚠️'}</span>
          <span className={styles['step-message']}>
            {step.message}
            <span className={`${styles['step-score']} ${qualityPassed ? styles['score-passed'] : styles['score-failed']}`}>
              质量: {step.quality_score !== undefined ? `${(step.quality_score * 10).toFixed(1)}/10` : 'N/A'}
            </span>
            <span className={`${styles['step-score']} ${consistencyPassed ? styles['score-passed'] : styles['score-failed']}`}>
              一致性: {step.consistency_score !== undefined ? `${(step.consistency_score * 10).toFixed(1)}/10` : 'N/A'}
            </span>
          </span>
        </div>
      );

    case 'consistency_check_start':
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-icon']}>🔍</span>
          <span className={styles['step-message']}>{step.message}</span>
        </div>
      );

    case 'consistency_check_complete':
      return (
        <div className={`${styles.step} ${step.consistency_passed ? styles['step-success'] : styles['step-warning']} ${containerClass}`}>
          <span className={styles['step-icon']}>{step.consistency_passed ? '✅' : '⚠️'}</span>
          <span className={styles['step-message']}>
            {step.message}
            {!step.consistency_passed && step.consistency_issues && step.consistency_issues.length > 0 && (
              <div className={styles['step-issues']}>
                {step.consistency_issues.slice(0, 2).map((issue, i) => (
                  <div key={i} className={styles['step-issue']}>• {issue}</div>
                ))}
              </div>
            )}
          </span>
        </div>
      );

    case 'rewrite_start':
      return (
        <div className={`${styles.step} ${styles['step-warning']} ${containerClass}`}>
          <span className={styles['step-icon']}>🔄</span>
          <span className={styles['step-message']}>
            {step.message}
            {step.quality_score !== undefined && (
              <span className={`${styles['step-score']} ${styles['score-failed']}`}>
                当前: 质量 {(step.quality_score * 10).toFixed(1)}/10, 一致性 {(step.consistency_score! * 10).toFixed(1)}/10
              </span>
            )}
          </span>
        </div>
      );

    case 'rewrite_attempt':
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-icon']}>🔄</span>
          <span className={styles['step-message']}>
            第 {step.rewrite_attempt} 次重写...
            <span className={styles['step-detail']}>
              {step.quality_score !== undefined && `质量: ${(step.quality_score * 10).toFixed(1)}/10`}
              {step.consistency_score !== undefined && ` | 一致性: ${(step.consistency_score * 10).toFixed(1)}/10`}
            </span>
          </span>
        </div>
      );

    case 'rewrite_llm_call':
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-icon']}>🤖</span>
          <span className={styles['step-message']}>
            {step.message}
            <span className={styles['step-detail']}>(第 {step.rewrite_attempt} 次重写)</span>
          </span>
        </div>
      );

    case 'rewrite_evaluation':
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-icon']}>📊</span>
          <span className={styles['step-message']}>
            {step.message}
            <span className={styles['step-detail']}>(第 {step.rewrite_attempt} 次重写)</span>
          </span>
        </div>
      );

    case 'rewrite_success':
      return (
        <div className={`${styles.step} ${styles['step-success']} ${containerClass}`}>
          <span className={styles['step-icon']}>✅</span>
          <span className={styles['step-message']}>
            {step.message}
            <span className={styles['step-detail']}>
              {step.quality_score !== undefined && `质量: ${(step.quality_score * 10).toFixed(1)}/10`}
              {step.consistency_score !== undefined && ` | 一致性: ${(step.consistency_score * 10).toFixed(1)}/10`}
            </span>
          </span>
        </div>
      );

    case 'rewrite_failed':
      return (
        <div className={`${styles.step} ${styles['step-warning']} ${containerClass}`}>
          <span className={styles['step-icon']}>⚠️</span>
          <span className={styles['step-message']}>
            {step.message}
            {(step.quality_issues || step.consistency_issues_2) && (
              <div className={styles['step-issues']}>
                {step.quality_issues?.slice(0, 2).map((issue, i) => (
                  <div key={`q-${i}`} className={styles['step-issue']}>• 质量: {issue}</div>
                ))}
                {step.consistency_issues_2?.slice(0, 2).map((issue, i) => (
                  <div key={`c-${i}`} className={styles['step-issue']}>• 一致性: {issue}</div>
                ))}
              </div>
            )}
          </span>
        </div>
      );

    case 'rewrite_error':
      return (
        <div className={`${styles.step} ${styles['step-error']} ${containerClass}`}>
          <span className={styles['step-icon']}>❌</span>
          <span className={styles['step-message']}>{step.message}</span>
        </div>
      );

    default:
      return (
        <div className={`${styles.step} ${styles['step-info']} ${containerClass}`}>
          <span className={styles['step-message']}>{step.message}</span>
        </div>
      );
  }
}

function getProviderName(provider: string): string {
  const names: Record<string, string> = {
    'qwen': '阿里云 Qwen',
    'deepseek': 'DeepSeek',
    'ark': '字节跳动 Doubao',
  };
  return names[provider] || provider;
}
