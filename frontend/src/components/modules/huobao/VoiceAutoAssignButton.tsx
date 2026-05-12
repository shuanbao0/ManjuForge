"use client";

import { Wand2 } from "lucide-react";
import { ActionButton } from "@/components/common/ActionButton";
import { useAutoVoices } from "@/hooks/useAutoVoices";

/**
 * One-click "auto-assign voices to all characters" trigger.
 *
 * Placed at the top of the Casting Room sidebar in VoiceActingStudio.
 * Respects the backend's chain rules: characters that already have a
 * ``voice_id`` or are ``locked`` keep their current voice. Empty
 * projects render the button disabled rather than hidden so the affordance
 * is discoverable.
 */
interface VoiceAutoAssignButtonProps {
  scriptId: string | undefined;
  characterCount: number;
  className?: string;
}

export default function VoiceAutoAssignButton({
  scriptId,
  characterCount,
  className,
}: VoiceAutoAssignButtonProps) {
  const action = useAutoVoices(scriptId);
  const disabled = !scriptId || characterCount === 0;
  return (
    <ActionButton
      action={action}
      args={[]}
      icon={<Wand2 size={14} />}
      variant="outline"
      size="sm"
      disabled={disabled}
      className={className}
      title={
        disabled
          ? "需要先提取角色才能自动分配音色"
          : "根据角色性别 / 性格自动从可用音色池里挑选并绑定"
      }
    >
      一键智能配音
    </ActionButton>
  );
}
