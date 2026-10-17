import React from 'react';
import { Clock, Coins, Zap } from 'lucide-react';
import type { TokenUsage } from './api';

export interface AssistantTurnMetricsProps {
  tokenUsage?: TokenUsage | null;
  elapsedMs?: number | null;
  timingsMs?: Record<string, number> | null;
}

const TIMING_LABELS: Record<string, string> = {
  db_before_turn: 'Ghi DB đầu lượt',
  agent_graph: 'Agent graph (tổng)',
  'db:ensure_chat_case': '  · DB: tìm/tạo case',
  'db:get_user': '  · DB: đọc user',
  'db:add_message': '  · DB: ghi tin nhắn',
  'cpu:triage_rules': '  · CPU: luật cấp cứu',
  'node:route_intent': '  · Node route_intent',
  'node:analyze': '  · Node analyze',
  'node:critic': '  · Node critic',
  'node:find_doctors': '  · Node find_doctors',
  'node:info_agent': '  · Node info_agent',
  'node:respond': '  · Node respond',
};

const EXCHANGE_RATE_USD_VND = 25500;
const fmt = (n: number) => n.toLocaleString('vi-VN');

/**
 * Hiển thị số liệu THẬT của lượt chat: token do provider trả về và độ trễ đo ở backend.
 * Không tự ước lượng: thiếu số liệu thì ẩn mục đó thay vì hiện số giả.
 */
export function AssistantTurnMetrics({ tokenUsage, elapsedMs, timingsMs }: AssistantTurnMetricsProps) {
  const hasTokens = tokenUsage?.total_tokens !== undefined && tokenUsage?.total_tokens !== null;
  const hasTime = typeof elapsedMs === 'number' && elapsedMs > 0;
  if (!hasTokens && !hasTime) return null;

  const total = tokenUsage?.total_tokens ?? 0;
  const prompt = tokenUsage?.prompt_tokens ?? 0;
  const output = tokenUsage?.completion_tokens ?? 0;
  const cached = tokenUsage?.cached_prompt_tokens ?? 0;
  const reasoning = tokenUsage?.reasoning_tokens ?? 0;
  const calls = tokenUsage?.llm_calls ?? 0;
  const saved = tokenUsage?.tokens_saved ?? 0;
  const isReal = tokenUsage?.execution_mode === 'provider_usage';
  const cacheRate = prompt > 0 ? Math.round((cached / prompt) * 100) : 0;

  let tokenDisplay = '';
  let tokenTooltip = '';
  if (hasTokens) {
    if (total === 0 && saved > 0) {
      tokenDisplay = `0 tokens (tiết kiệm ${fmt(saved)})`;
      tokenTooltip = `Xử lý bằng rule/cache, không gọi LLM (tiết kiệm ${fmt(saved)} tokens)`;
    } else {
      tokenDisplay = `${fmt(total)} tokens · vào ${fmt(prompt)}${cached > 0 ? ` (cache ${cacheRate}%)` : ''} · ra ${fmt(output)}`;
      tokenTooltip = [
        `${isReal ? 'Số liệu thật từ provider' : 'Số liệu ước tính (không phải usage thật)'}`,
        `Tổng: ${fmt(total)} tokens`,
        `Đầu vào: ${fmt(prompt)} (trúng cache: ${fmt(cached)}, chưa cache: ${fmt(Math.max(prompt - cached, 0))})`,
        `Đầu ra: ${fmt(output)}${reasoning > 0 ? ` (trong đó thinking: ${fmt(reasoning)})` : ''}`,
        calls > 0 ? `Số lần gọi LLM: ${calls}` : '',
      ]
        .filter(Boolean)
        .join('\n');
    }
  }

  let costDisplay = '';
  let costTooltip = '';
  const costUsd = tokenUsage?.estimated_cost_usd;
  if (hasTokens && typeof costUsd === 'number') {
    if (costUsd === 0) {
      costDisplay = '$0.00';
      costTooltip = 'Chi phí: $0.00';
    } else {
      const usd = costUsd < 0.0001 ? `$${costUsd.toFixed(5)}` : `$${costUsd.toFixed(4)}`;
      const vnd = costUsd * EXCHANGE_RATE_USD_VND;
      costDisplay = `~${usd}`;
      costTooltip = `Chi phí quy đổi theo giá DeepSeek (cache hit/miss/output): ${usd} ≈ ${vnd.toFixed(1)} đ`;
    }
  }

  const timeDisplay = hasTime ? `${((elapsedMs as number) / 1000).toFixed(2)}s` : '';
  const breakdown = timingsMs
    ? Object.entries(timingsMs)
        .map(([key, ms]) => `${TIMING_LABELS[key] ?? key}: ${Math.round(ms).toLocaleString('vi-VN')} ms`)
        .join('\n')
    : '';
  const timeTooltip = hasTime
    ? [
        `Độ trễ cả lượt (backend, từ lúc nhận đến lúc có câu trả lời): ${Math.round(elapsedMs as number).toLocaleString('vi-VN')} ms`,
        breakdown,
      ]
        .filter(Boolean)
        .join('\n')
    : '';

  const itemClass =
    'inline-flex items-center gap-1 hover:text-slate-600 dark:hover:text-slate-300 transition-colors cursor-help';
  const dot = <span className="text-slate-300 dark:text-slate-700">·</span>;

  return (
    <div
      aria-label="Thông số kỹ thuật lượt hội thoại"
      className="mb-2 pb-1.5 border-b border-slate-100 dark:border-slate-800/80 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] sm:text-[10.5px] text-slate-400 dark:text-slate-400 font-mono tracking-tight select-none"
    >
      {hasTime && (
        <span className={itemClass} title={timeTooltip}>
          <Clock className="h-2.5 w-2.5 text-blue-500/80 dark:text-cyan-400/80" />
          <span>{timeDisplay}</span>
        </span>
      )}
      {hasTime && hasTokens && dot}
      {hasTokens && (
        <span className={itemClass} title={tokenTooltip}>
          <Zap className="h-2.5 w-2.5 text-amber-500/80 dark:text-amber-400/80" />
          <span>{tokenDisplay}</span>
        </span>
      )}
      {costDisplay && (
        <>
          {dot}
          <span className={itemClass} title={costTooltip}>
            <Coins className="h-2.5 w-2.5 text-emerald-500/80 dark:text-emerald-400/80" />
            <span>{costDisplay}</span>
          </span>
        </>
      )}
    </div>
  );
}
