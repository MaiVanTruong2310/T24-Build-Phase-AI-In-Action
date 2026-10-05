import React from 'react';
import { Clock, Coins, Zap } from 'lucide-react';
import type { TokenUsage } from './api';

export interface AssistantTurnMetricsProps {
  tokenUsage?: TokenUsage | null;
  elapsedMs?: number | null;
  text?: string;
}

const EXCHANGE_RATE_USD_VND = 25500;

export function AssistantTurnMetrics({ tokenUsage, elapsedMs, text }: AssistantTurnMetricsProps) {
  // 1. Calculate tokens
  let totalTokens: number;
  let promptTokens: number | undefined;
  let completionTokens: number | undefined;
  let tokensSaved = 0;

  if (tokenUsage && tokenUsage.total_tokens !== undefined && tokenUsage.total_tokens !== null) {
    totalTokens = tokenUsage.total_tokens;
    promptTokens = tokenUsage.prompt_tokens;
    completionTokens = tokenUsage.completion_tokens;
    tokensSaved = tokenUsage.tokens_saved || 0;
  } else if (text) {
    // Graceful estimation for legacy turns or offline responses
    const estimatedCompletion = Math.max(10, Math.round(text.length / 3.6));
    const estimatedPrompt = 45;
    totalTokens = estimatedPrompt + estimatedCompletion;
    promptTokens = estimatedPrompt;
    completionTokens = estimatedCompletion;
  } else {
    return null;
  }

  // 2. Calculate cost
  let costUsd: number;
  if (tokenUsage && tokenUsage.estimated_cost_usd !== undefined && tokenUsage.estimated_cost_usd !== null) {
    costUsd = tokenUsage.estimated_cost_usd;
  } else {
    // gpt-4o-mini baseline: ~$0.15/1M prompt, $0.60/1M completion
    const pTok = promptTokens ?? 40;
    const cTok = completionTokens ?? (totalTokens - pTok);
    costUsd = (pTok * 0.15 + cTok * 0.60) / 1_000_000;
  }

  // Format tokens string
  let tokenDisplay: string;
  let tokenTooltip: string;
  if (totalTokens === 0 && tokensSaved > 0) {
    tokenDisplay = `0 tokens (tiết kiệm ${tokensSaved.toLocaleString()})`;
    tokenTooltip = `Được xử lý tức thì qua Zero-Token Cache/Fast-Path (Tiết kiệm ${tokensSaved.toLocaleString()} tokens)`;
  } else {
    tokenDisplay = `${totalTokens.toLocaleString()} tokens`;
    tokenTooltip = promptTokens !== undefined && completionTokens !== undefined
      ? `Tổng tokens: ${totalTokens.toLocaleString()} (Prompt: ${promptTokens.toLocaleString()} / Output: ${completionTokens.toLocaleString()})`
      : `Tổng số tokens: ${totalTokens.toLocaleString()}`;
  }

  // Format cost string
  let costDisplay: string;
  let costTooltip: string;
  if (costUsd === 0) {
    costDisplay = '$0.00';
    costTooltip = 'Chi phí: $0.00 (Miễn phí qua Fast-Path/Cache)';
  } else {
    const usdFormatted = costUsd < 0.0001 ? `$${costUsd.toFixed(5)}` : `$${costUsd.toFixed(4)}`;
    const costVnd = costUsd * EXCHANGE_RATE_USD_VND;
    const vndFormatted = costVnd < 1 ? `${costVnd.toFixed(1)} đ` : `${Math.round(costVnd).toLocaleString('vi-VN')} đ`;
    costDisplay = `~${usdFormatted} (~${vndFormatted})`;
    costTooltip = `Ước tính chi phí: ${usdFormatted} (~${costVnd.toFixed(2)} VNĐ)`;
  }

  // 3. Format response time (Thời gian phản hồi)
  let timeDisplay: string | null = null;
  let timeTooltip = 'Thời gian xử lý và phản hồi';
  if (elapsedMs !== undefined && elapsedMs !== null && elapsedMs > 0) {
    if (elapsedMs >= 1000) {
      timeDisplay = `${(elapsedMs / 1000).toFixed(2)}s`;
      timeTooltip = `Thời gian phản hồi: ${(elapsedMs / 1000).toFixed(2)} giây (${Math.round(elapsedMs).toLocaleString('vi-VN')} ms)`;
    } else {
      timeDisplay = `${(elapsedMs / 1000).toFixed(2)}s`;
      timeTooltip = `Thời gian phản hồi: ${Math.round(elapsedMs)} ms (${(elapsedMs / 1000).toFixed(2)}s)`;
    }
  }

  return (
    <div
      aria-label="Thông số kỹ thuật lượt hội thoại"
      className="mt-2.5 pt-1.5 border-t border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] sm:text-[10.5px] text-slate-400 dark:text-slate-400 font-mono tracking-tight select-none"
    >
      {/* Tokens */}
      <span
        className="inline-flex items-center gap-1 hover:text-slate-600 dark:hover:text-slate-300 transition-colors cursor-help"
        title={tokenTooltip}
      >
        <Zap className="h-2.5 w-2.5 text-amber-500/80 dark:text-amber-400/80" />
        <span>{tokenDisplay}</span>
      </span>

      <span className="text-slate-300 dark:text-slate-700">·</span>

      {/* Cost */}
      <span
        className="inline-flex items-center gap-1 hover:text-slate-600 dark:hover:text-slate-300 transition-colors cursor-help"
        title={costTooltip}
      >
        <Coins className="h-2.5 w-2.5 text-emerald-500/80 dark:text-emerald-400/80" />
        <span>{costDisplay}</span>
      </span>

      {/* Response time */}
      {timeDisplay && (
        <>
          <span className="text-slate-300 dark:text-slate-700">·</span>
          <span
            className="inline-flex items-center gap-1 hover:text-slate-600 dark:hover:text-slate-300 transition-colors cursor-help"
            title={timeTooltip}
          >
            <Clock className="h-2.5 w-2.5 text-blue-500/80 dark:text-cyan-400/80" />
            <span>{timeDisplay}</span>
          </span>
        </>
      )}
    </div>
  );
}
