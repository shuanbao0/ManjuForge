"use client";

import { useState } from "react";
import { Grid3x3 } from "lucide-react";
import BatchKeyframesDialog from "./BatchKeyframesDialog";

/**
 * Toolbar button that opens the BatchKeyframesDialog.
 *
 * Kept as a thin wrapper so StoryboardComposer can drop in one line
 * (`<BatchKeyframesButton ... />`) without managing dialog open/close
 * state itself. The dialog handles its own selection / mode / submit
 * lifecycle and refreshes the project after success.
 */
interface BatchKeyframesButtonProps {
  scriptId: string | undefined;
  frames: any[];
  className?: string;
}

export default function BatchKeyframesButton({
  scriptId,
  frames,
  className,
}: BatchKeyframesButtonProps) {
  const [open, setOpen] = useState(false);
  const disabled = !scriptId || frames.length === 0;
  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        disabled={disabled}
        title={
          disabled
            ? "需要先有分镜帧"
            : "网格批量出图(Seedream 一次出 9 张,其他 vendor 自动逐镜)"
        }
        className={`inline-flex items-center gap-1.5 text-xs bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/30 px-3 py-1.5 rounded-lg text-gray-200 hover:text-white transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${className ?? ""}`}
      >
        <Grid3x3 size={14} />
        批量出图
      </button>
      {open && (
        <BatchKeyframesDialog
          scriptId={scriptId}
          frames={frames}
          onClose={() => setOpen(false)}
        />
      )}
    </>
  );
}
