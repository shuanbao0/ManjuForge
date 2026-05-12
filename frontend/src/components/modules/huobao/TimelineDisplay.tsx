"use client";

import { useMemo } from "react";
import clsx from "clsx";

/**
 * Adapter that parses the backend's timeline-text format
 * (``<location>...<role>...<n0-3>action</n0-3><n3-6>...</n3-6>...``)
 * into structured React nodes — color-coded segment bars with hover
 * tooltips showing the per-window text.
 *
 * On parse failure (unexpected format) renders the raw string in a
 * monospace block so the user can still see something useful instead
 * of a blank panel.
 */
interface TimelineDisplayProps {
  timeline: string;
  className?: string;
}

interface Segment {
  start: number;
  end: number;
  text: string;
}

interface ParseResult {
  meta: { location?: string; roles: string[]; sound?: string };
  segments: Segment[];
  raw: string;
}

function parseTimeline(text: string): ParseResult | null {
  const meta: ParseResult["meta"] = { roles: [] };
  // Greedy single-line meta tags
  const locMatch = text.match(/<location>(.*?)<\/location>/);
  if (locMatch) meta.location = locMatch[1];
  const soundMatch = text.match(/<sound>(.*?)<\/sound>/);
  if (soundMatch) meta.sound = soundMatch[1];
  const roleMatches = Array.from(text.matchAll(/<role>(.*?)<\/role>/g));
  for (const m of roleMatches) meta.roles.push(m[1]);

  // <n{start}-{end}>...</n{start}-{end}> — accept newlines inside body
  const segments: Segment[] = [];
  const segRegex = /<n(\d+)-(\d+)>([\s\S]*?)<\/n\1-\2>/g;
  for (const m of Array.from(text.matchAll(segRegex))) {
    segments.push({
      start: parseInt(m[1], 10),
      end: parseInt(m[2], 10),
      text: m[3].trim(),
    });
  }
  if (segments.length === 0) return null;
  return { meta, segments, raw: text };
}

const SEGMENT_COLORS = [
  "bg-blue-500/20 border-blue-400/40",
  "bg-purple-500/20 border-purple-400/40",
  "bg-green-500/20 border-green-400/40",
  "bg-amber-500/20 border-amber-400/40",
  "bg-rose-500/20 border-rose-400/40",
  "bg-cyan-500/20 border-cyan-400/40",
];

export default function TimelineDisplay({ timeline, className }: TimelineDisplayProps) {
  const parsed = useMemo(() => parseTimeline(timeline || ""), [timeline]);

  if (!parsed) {
    return (
      <pre
        className={clsx(
          "text-xs font-mono whitespace-pre-wrap text-gray-400 bg-black/30 rounded p-3 overflow-auto",
          className,
        )}
      >
        {timeline}
      </pre>
    );
  }

  const totalDuration = parsed.segments[parsed.segments.length - 1]?.end ?? 1;
  return (
    <div className={clsx("space-y-3", className)}>
      {/* Meta strip */}
      <div className="flex flex-wrap gap-2 text-[11px]">
        {parsed.meta.location && (
          <span className="px-2 py-0.5 rounded bg-white/5 text-gray-300">
            📍 {parsed.meta.location}
          </span>
        )}
        {parsed.meta.roles.map((role) => (
          <span
            key={role}
            className="px-2 py-0.5 rounded bg-blue-500/15 text-blue-300"
          >
            👤 {role}
          </span>
        ))}
        {parsed.meta.sound && (
          <span className="px-2 py-0.5 rounded bg-amber-500/15 text-amber-300">
            🔊 {parsed.meta.sound}
          </span>
        )}
      </div>

      {/* Proportional segment bar — width ∝ duration */}
      <div className="flex h-2 rounded overflow-hidden bg-black/30">
        {parsed.segments.map((seg, i) => {
          const pct = ((seg.end - seg.start) / totalDuration) * 100;
          return (
            <div
              key={i}
              className={clsx("border-r border-black/40 last:border-r-0", SEGMENT_COLORS[i % SEGMENT_COLORS.length])}
              style={{ width: `${pct}%` }}
              title={`${seg.start}-${seg.end}s: ${seg.text}`}
            />
          );
        })}
      </div>

      {/* Per-segment text */}
      <div className="space-y-1.5">
        {parsed.segments.map((seg, i) => (
          <div
            key={i}
            className={clsx(
              "flex gap-3 text-xs border-l-2 pl-2 py-0.5",
              SEGMENT_COLORS[i % SEGMENT_COLORS.length].split(" ").find((c) => c.startsWith("border-")) ?? "border-white/20",
            )}
          >
            <span className="font-mono text-gray-500 shrink-0">
              {seg.start}-{seg.end}s
            </span>
            <span className="text-gray-200">{seg.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
