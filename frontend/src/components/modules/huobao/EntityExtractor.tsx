"use client";

import { useState, useRef, useEffect } from "react";
import { Sparkles, ChevronDown } from "lucide-react";
import clsx from "clsx";
import { ActionButton } from "@/components/common/ActionButton";
import { useEntityExtraction } from "@/hooks/useEntityExtraction";

/**
 * Smart entity extraction trigger with a dropdown for strategy choice.
 *
 * Default action: incremental (project-level dedup). Click the chevron
 * to reveal the full-extraction option. Hidden when no script is
 * active. Standalone projects (no ``series_id``) still benefit from
 * the safety-net dedup so the same button works in either context.
 */
interface EntityExtractorProps {
  scriptId: string | undefined;
}

export default function EntityExtractor({ scriptId }: EntityExtractorProps) {
  const action = useEntityExtraction(scriptId);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // Click-outside dismissal — common pattern for headerless menus.
  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    window.addEventListener("mousedown", onClick);
    return () => window.removeEventListener("mousedown", onClick);
  }, [menuOpen]);

  const disabled = !scriptId;
  return (
    <div className="relative inline-flex" ref={menuRef}>
      <ActionButton
        action={action}
        args={["incremental"]}
        icon={<Sparkles size={14} />}
        variant="outline"
        size="sm"
        disabled={disabled}
        title="增量提取:LLM 看到已有 Series 实体,优先复用而不是重复创建"
        className="rounded-r-none border-r-0"
      >
        智能补齐实体
      </ActionButton>
      <button
        type="button"
        onClick={() => !disabled && setMenuOpen((v) => !v)}
        disabled={disabled || action.isPending}
        title="选择提取策略"
        className={clsx(
          "h-8 px-2 border border-white/15 bg-transparent hover:bg-white/5 text-white",
          "rounded-r-lg disabled:opacity-50 disabled:cursor-not-allowed",
        )}
      >
        <ChevronDown size={14} />
      </button>
      {menuOpen && !action.isPending && (
        <div className="absolute right-0 top-full mt-1 w-56 bg-[#1a1a1a] border border-white/10 rounded-lg shadow-2xl z-50 overflow-hidden">
          <button
            type="button"
            onClick={() => {
              setMenuOpen(false);
              action.run("full");
            }}
            className="w-full text-left px-3 py-2 text-xs text-gray-200 hover:bg-white/10"
          >
            <div className="font-bold">全量重提</div>
            <div className="text-gray-500 mt-0.5">
              重新扫描全文,忽略已有 Series 实体(慎用,可能产生重复)
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
