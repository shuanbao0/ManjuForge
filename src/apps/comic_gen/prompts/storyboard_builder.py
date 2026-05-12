"""Builder for the storyboard-analysis system prompt.

The previous implementation lived as a 60-line f-string inside
``ScriptProcessor.analyze_to_storyboard``. Adding new outputs (BGM/SFX
prompts, future audio_atoms, etc.) meant editing that wall of text
in-place and re-checking the JSON schema by eye.

This module replaces that with an additive Builder: each
``with_*`` call appends an instruction block and contributes its
fields to the JSON example, so callers can opt in/out of stages
without copy-pasting.

Design notes
~~~~~~~~~~~~
* **Pure**: no LLM calls; the builder only returns a string.
* **Idempotent**: each ``with_*`` may be called once; repeats are
  no-ops to keep the prompt deterministic across mis-ordered calls.
* **Forward-compatible**: ``build()`` re-renders the JSON example from
  the accumulated field dict, so adding a new field in one ``with_*``
  is enough — no separate "example" branch to maintain.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# ── Reusable instruction blocks ─────────────────────────────────────────
# Each block is a self-contained section of the final system prompt.
# Splitting them out lets tests assert on a single block without
# loading the entire 600-line prompt into the assertion.

_ROLE_BLOCK = """\
# 角色
你是一名电影级的分镜师（Storyboard Artist）和导演。你的任务是将剧本文本拆解为可供 AI 视频模型生成的一系列精细分镜帧。

# 任务目标
不仅仅是提取文本，而是要进行**视觉化拆解**。你需要将剧本中的文字转化为一系列连续的、单一动作的视觉画面。"""

_SCRIPT_FORMAT_BLOCK = """\
# 剧本格式说明
剧本遵循以下格式：
- **场景标题行**: `1-1 地点名称 [时间] [内/外]`
- **人物行**: `人物： 角色名1，角色名2`
- **动作描述**: 以 `△` 开头，描述画面中发生的动作
- **对话**: `角色名（情绪）： 对话内容`，或 `角色名 (V.O.)：` 表示画外音"""

_VISUAL_ATOMS_BLOCK = """\
# 核心规则 (CRITICAL)
1. **视觉节拍拆解 (VISUAL ATOMIZATION)**:
   - 如果一行动作描述包含多个连续动作，**必须**将其拆分为多个分镜帧。
   - 每个分镜只应包含一个清晰的主要动作，时长控制在 3-5 秒。
2. **合并动作描述 (MERGE ACTION)**:
   - **`action_description` 字段必须包含画面中发生的所有动态要素**。
   - 包括：人物的神态/微表情 + 肢体动作 + 道具的物理运动（如手机震动、烟雾缭绕）。
   - 不要遗漏非人物主体的动作（如"车门打开"、"杯子摔碎"）。
3. **角色可见性**:
   - `character_ref_names` 只列出**当前分镜画面中可见**的角色。
4. **实体约束**:
   - 场景名、角色名、道具名必须严格匹配"已提取的实体"。
5. **语言**: 所有输出必须使用简体中文。
6. **标签与时长 (LABEL & DURATION)**:
   - `title`: 3-5 字镜头小标题(如"震动惊醒"、"破门而入"),便于 UI 列表速览。
   - `duration_seconds`: 该镜头的计划拍摄时长,整数秒,范围 3-10。"""

# The audio-atoms block adds two fields per frame:
# - ``bgm_prompt``: music style description, consumed by AudioGenerator.generate_bgm
# - ``sfx_prompt``: sound effect description, consumed by AudioGenerator.generate_sfx
# The model is instructed to keep them *short* — these become prompts to
# downstream MusicGen/SFX vendors, not narrative descriptions.
_AUDIO_ATOMS_BLOCK = """\
# 音频原子 (AUDIO ATOMS)
在每个分镜里同时给出**配乐**与**音效**的关键词级提示词，供后续 MusicGen / SFX 生成使用：
- `bgm_prompt`: **音乐风格 + 情绪 + 乐器**，10-30 字。例：「悬疑钢琴单音 + 低频心跳」。
- `sfx_prompt`: **画面里能听到的声音事件**，优先关键动作 + 环境音，10-30 字。例：「手机震动声 + 远处车流」。
若画面纯静默或无配乐意图，对应字段可以为 `null`，但不要省略键。"""


# ── JSON example skeleton ───────────────────────────────────────────────
# Built incrementally by ``with_*`` calls. Single source of truth for
# both the schema documentation and the example shown to the LLM.

_BASE_EXAMPLE_FRAME: Dict[str, Any] = {
    "title": "震动惊醒",
    "duration_seconds": 4,
    "scene_ref_name": "卧室",
    "character_ref_names": ["叶墨"],
    "prop_ref_names": ["手机"],
    "visual_atmosphere": "昏暗的卧室，窗外透进冷色调月光",
    "action_description": "手机在床头柜上疯狂震动。叶墨眉头紧锁，烦躁地翻身，肩膀挤压枕头产生形变",
    "shot_size": "中景",
    "camera_angle": "俯视",
    "camera_movement": "静止",
    "dialogue": "妈，这才几点啊！",
    "speaker": "叶墨",
}

_AUDIO_EXAMPLE_FIELDS: Dict[str, Any] = {
    "bgm_prompt": "低频环境氛围 + 偶发钢琴单音",
    "sfx_prompt": "手机震动声 + 床单摩擦声",
}


@dataclass
class StoryboardPromptBuilder:
    """Composable builder for the storyboard-analysis system prompt.

    Typical usage::

        prompt = (
            StoryboardPromptBuilder()
                .with_role()
                .with_script_format()
                .with_entities(entities_json)
                .with_visual_atoms()
                .with_audio_atoms()
                .build(text)
        )

    Call order doesn't change the output; each block is appended at
    ``build()`` time in canonical order.
    """

    _enabled: Dict[str, bool] = field(default_factory=dict)
    _entities_json: Optional[Dict[str, Any]] = None

    def with_role(self) -> "StoryboardPromptBuilder":
        self._enabled["role"] = True
        return self

    def with_script_format(self) -> "StoryboardPromptBuilder":
        self._enabled["script_format"] = True
        return self

    def with_entities(self, entities_json: Dict[str, Any]) -> "StoryboardPromptBuilder":
        """Inject the resolved character/scene/prop catalog as context."""
        self._enabled["entities"] = True
        self._entities_json = entities_json or {}
        return self

    def with_visual_atoms(self) -> "StoryboardPromptBuilder":
        self._enabled["visual_atoms"] = True
        return self

    def with_audio_atoms(self) -> "StoryboardPromptBuilder":
        """Ask the LLM to emit per-frame BGM/SFX prompts alongside visuals."""
        self._enabled["audio_atoms"] = True
        return self

    # ── Rendering ──────────────────────────────────────────────────────

    def _render_entities(self) -> str:
        ent = self._entities_json or {}
        return (
            "# 已提取的实体上下文\n"
            "Characters:\n"
            f"{json.dumps(ent.get('characters', []), ensure_ascii=False, indent=2)}\n\n"
            "Scenes:\n"
            f"{json.dumps(ent.get('scenes', []), ensure_ascii=False, indent=2)}\n\n"
            "Props:\n"
            f"{json.dumps(ent.get('props', []), ensure_ascii=False, indent=2)}"
        )

    def _render_output_format(self) -> str:
        """Compose the example frame dict based on which blocks are enabled."""
        example_frame = dict(_BASE_EXAMPLE_FRAME)
        if self._enabled.get("audio_atoms"):
            example_frame.update(_AUDIO_EXAMPLE_FIELDS)
        # Second example showcases atomization (two frames for one beat)
        second_frame = {
            "title": "惊恐坐起",
            "duration_seconds": 3,
            "scene_ref_name": "卧室",
            "character_ref_names": ["叶墨"],
            "prop_ref_names": [],
            "visual_atmosphere": "昏暗的卧室",
            "action_description": "被子滑落，叶墨猛地坐起，一脸惊恐",
            "shot_size": "特写",
            "camera_angle": "平视",
            "camera_movement": "快速推镜头",
            "dialogue": "已经来了？",
            "speaker": "叶墨",
        }
        if self._enabled.get("audio_atoms"):
            second_frame["bgm_prompt"] = "突进的弦乐重音"
            second_frame["sfx_prompt"] = "被子滑落声 + 急促呼吸"

        example = {"frames": [example_frame, second_frame]}
        # ``indent=4`` matches the original hand-written prompt's style so
        # diff against the legacy version stays small for code-review.
        return (
            "# 输出格式\n"
            "返回一个包含 `frames` 数组的 JSON 对象。不要包含 Markdown 格式标记（如 ```json）。\n\n"
            + json.dumps(example, ensure_ascii=False, indent=4)
        )

    def build(self, text: str) -> str:
        """Render the full system prompt with the user's script appended."""
        parts: List[str] = []
        if self._enabled.get("role"):
            parts.append(_ROLE_BLOCK)
        if self._enabled.get("script_format"):
            parts.append(_SCRIPT_FORMAT_BLOCK)
        if self._enabled.get("entities"):
            parts.append(self._render_entities())
        if self._enabled.get("visual_atoms"):
            parts.append(_VISUAL_ATOMS_BLOCK)
        if self._enabled.get("audio_atoms"):
            parts.append(_AUDIO_ATOMS_BLOCK)
        parts.append(self._render_output_format())
        parts.append(f"# 剧本内容\n{text}")
        return "\n\n".join(parts)


__all__ = ["StoryboardPromptBuilder"]
