"use client";

import { useState } from "react";
import { FileText, ScrollText } from "lucide-react";
import clsx from "clsx";
import { ActionButton } from "@/components/common/ActionButton";
import { useScreenplayRewrite } from "@/hooks/useScreenplayRewrite";

/**
 * Toggle pair for "原文 / 剧本格式" + a rewrite trigger.
 *
 * When ``formattedText`` is empty the "剧本格式" tab shows a generation
 * CTA; once populated it becomes a read-only viewer. Original text
 * keeps editing rights — the rewrite is non-destructive, the rewriter
 * never clobbers ``original_text``.
 */
interface ScreenplayRewriterProps {
  scriptId: string | undefined;
  originalText: string;
  formattedText: string | undefined;
  /** Renders the textarea for the active tab — caller controls editing. */
  renderEditor: (args: {
    activeText: string;
    readOnly: boolean;
    onChange?: (value: string) => void;
  }) => React.ReactNode;
  /** Edit handler for the original-text tab. Optional — pass through
   *  the existing setScript / updateProject wiring. */
  onOriginalChange?: (value: string) => void;
}

type Tab = "original" | "formatted";

export default function ScreenplayRewriter({
  scriptId,
  originalText,
  formattedText,
  renderEditor,
  onOriginalChange,
}: ScreenplayRewriterProps) {
  const [tab, setTab] = useState<Tab>("original");
  const rewrite = useScreenplayRewrite(scriptId);
  const hasFormatted = !!formattedText && formattedText.trim().length > 0;

  return (
    <div className="flex flex-col h-full w-full">
      {/* Tab strip */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-white/10 bg-black/10">
        <button
          type="button"
          onClick={() => setTab("original")}
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 h-7 rounded-md text-xs font-medium transition-colors",
            tab === "original"
              ? "bg-white/10 text-white"
              : "text-gray-400 hover:text-white hover:bg-white/5",
          )}
        >
          <FileText size={12} /> 原文
        </button>
        <button
          type="button"
          onClick={() => setTab("formatted")}
          className={clsx(
            "inline-flex items-center gap-1.5 px-3 h-7 rounded-md text-xs font-medium transition-colors",
            tab === "formatted"
              ? "bg-white/10 text-white"
              : "text-gray-400 hover:text-white hover:bg-white/5",
            !hasFormatted && "text-gray-500",
          )}
        >
          <ScrollText size={12} /> 剧本格式
          {hasFormatted && (
            <span className="ml-1 inline-block w-1.5 h-1.5 rounded-full bg-primary" />
          )}
        </button>
        <div className="flex-1" />
        {tab === "formatted" && (
          <ActionButton
            action={rewrite}
            args={[]}
            variant={hasFormatted ? "ghost" : "primary"}
            size="sm"
            disabled={!scriptId || !originalText}
          >
            {hasFormatted ? "重新格式化" : "生成剧本格式"}
          </ActionButton>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 relative overflow-hidden">
        {tab === "original" && (
          <div className="absolute inset-0">
            {renderEditor({
              activeText: originalText,
              readOnly: false,
              onChange: onOriginalChange,
            })}
          </div>
        )}
        {tab === "formatted" && (
          <div className="absolute inset-0">
            {hasFormatted ? (
              renderEditor({
                activeText: formattedText!,
                readOnly: true,
              })
            ) : (
              <div className="h-full flex items-center justify-center text-center px-6">
                <div className="max-w-md text-sm text-gray-400 space-y-2">
                  <p className="text-gray-300 font-medium">
                    把小说原文格式化成短剧脚本格式
                  </p>
                  <p>
                    自动加入场景标题、人物行、△ 动作行、对话格式;
                    每场限制 30-60 秒,禁用镜头术语,扩写比例 ≤30%。
                  </p>
                  <p>下游"提取实体 / 分镜分析"读到格式化版本后,结果会更稳定。</p>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
