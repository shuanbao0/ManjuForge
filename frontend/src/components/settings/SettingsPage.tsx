"use client";

import { useEffect, useState } from "react";
import {
  Save, Settings, MessageSquareCode, ShieldCheck, Cpu,
  Layout, User as UserIcon, Building, Box,
} from "lucide-react";
import { ASPECT_RATIOS } from "@/store/projectStore";
import { InstanceList } from "./InstanceList";

// ─────────────────────────────────────────────────────────────────────────
// Settings page — fully driven by ModelInstance now. Vendor + key
// configuration moves into the InstanceList CRUD; this page keeps:
//   1. The instance list (primary surface).
//   2. Object storage credentials (per-user, separate concern).
//   3. Default aspect ratios + system prompts (browser-local prefs).
// ─────────────────────────────────────────────────────────────────────────

const LS_KEY_RATIO = "manju_forge_default_aspect_ratios";
const LS_KEY_PROMPT = "manju_forge_default_prompt_config";

interface DefaultAspectRatios {
  character_aspect_ratio: string;
  scene_aspect_ratio: string;
  prop_aspect_ratio: string;
  storyboard_aspect_ratio: string;
}

interface DefaultPromptConfig {
  storyboard_polish: string;
  video_polish: string;
  r2v_polish: string;
}

function loadFromLS<T>(key: string, fallback: T): T {
  if (typeof window === "undefined") return fallback;
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallback;
  } catch {
    return fallback;
  }
}


export default function SettingsPage() {
  const [aspectDefaults, setAspectDefaults] = useState<DefaultAspectRatios>(() =>
    loadFromLS(LS_KEY_RATIO, {
      character_aspect_ratio: "9:16",
      scene_aspect_ratio: "16:9",
      prop_aspect_ratio: "1:1",
      storyboard_aspect_ratio: "16:9",
    }),
  );

  const [promptConfig, setPromptConfig] = useState<DefaultPromptConfig>(() =>
    loadFromLS(LS_KEY_PROMPT, { storyboard_polish: "", video_polish: "", r2v_polish: "" }),
  );

  useEffect(() => {
    // Migrate the old combined model+ratio LS key if present (one-shot).
    const legacy = localStorage.getItem("manju_forge_default_model_settings");
    if (legacy && !localStorage.getItem(LS_KEY_RATIO)) {
      try {
        const parsed = JSON.parse(legacy);
        const next = {
          character_aspect_ratio: parsed.character_aspect_ratio ?? "9:16",
          scene_aspect_ratio: parsed.scene_aspect_ratio ?? "16:9",
          prop_aspect_ratio: parsed.prop_aspect_ratio ?? "1:1",
          storyboard_aspect_ratio: parsed.storyboard_aspect_ratio ?? "16:9",
        };
        localStorage.setItem(LS_KEY_RATIO, JSON.stringify(next));
        setAspectDefaults(next);
      } catch {
        /* ignore */
      }
    }
  }, []);

  const handleSaveAspectRatios = () => {
    localStorage.setItem(LS_KEY_RATIO, JSON.stringify(aspectDefaults));
    alert("默认画幅已保存");
  };

  const handleSavePromptDefaults = () => {
    localStorage.setItem(LS_KEY_PROMPT, JSON.stringify(promptConfig));
    alert("默认 prompt 已保存");
  };

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl space-y-8">
      {/* ── Header ── */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-lg">
          <ShieldCheck size={20} className="text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-display font-bold text-white">设置</h1>
          <p className="text-xs text-gray-500">配置你的模型实例,然后在每个项目里挑选要用哪一个</p>
        </div>
      </div>

      {/* ── Model instances (primary surface) ── */}
      <section className="glass-panel rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-lg">
            <Cpu size={20} className="text-amber-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">我的模型实例</h2>
            <p className="text-xs text-gray-500">
              每个生成阶段(LLM / 图像 / 视频 / 配音)都是独立实例 —
              同类型可配多个,项目里按需切换。凭证加密存于服务器侧。
            </p>
          </div>
        </div>

        <InstanceList />
      </section>

      {/* ── Default aspect ratios (browser-local prefs) ── */}
      <section className="glass-panel rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg">
            <Settings size={20} className="text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">默认画幅</h2>
            <p className="text-xs text-gray-500">为新项目预填的画幅(仅当前浏览器)</p>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          {([
            { key: "character_aspect_ratio" as const, label: "Character", icon: UserIcon },
            { key: "scene_aspect_ratio" as const, label: "Scene", icon: Building },
            { key: "prop_aspect_ratio" as const, label: "Prop", icon: Box },
            { key: "storyboard_aspect_ratio" as const, label: "Storyboard", icon: Layout },
          ] as const).map(({ key, label, icon: Icon }) => (
            <div key={key} className="space-y-2">
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Icon size={12} />
                <label>{label}</label>
              </div>
              <div className="space-y-1">
                {ASPECT_RATIOS.map((ratio) => (
                  <button
                    key={ratio.id}
                    onClick={() => setAspectDefaults((s) => ({ ...s, [key]: ratio.id }))}
                    className={`w-full flex flex-col items-center py-2 px-2 rounded border transition-all ${aspectDefaults[key] === ratio.id ? "border-blue-500/50 bg-blue-500/10" : "border-white/10 hover:border-white/20 bg-white/5"}`}
                  >
                    <span className="text-xs font-medium text-white">{ratio.name}</span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleSaveAspectRatios}
            className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white text-sm font-medium rounded-lg transition-all"
          >
            <Save size={16} />
            保存默认画幅
          </button>
        </div>
      </section>

      {/* ── Default polish prompts (browser-local prefs) ── */}
      <section className="glass-panel rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <MessageSquareCode size={20} className="text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">默认提示词配置</h2>
            <p className="text-xs text-gray-500">为新项目预填的系统 prompt(留空使用内置默认)</p>
          </div>
        </div>

        {(
          [
            { key: "storyboard_polish" as const, label: "Storyboard 润色", desc: "分镜/图片 prompt 润色 system prompt" },
            { key: "video_polish" as const, label: "I2V 润色", desc: "Image-to-Video prompt 润色 system prompt" },
            { key: "r2v_polish" as const, label: "R2V 润色", desc: "Reference-to-Video prompt 润色 system prompt" },
          ] as const
        ).map((section) => (
          <div key={section.key} className="space-y-2">
            <h3 className="text-sm font-bold text-white">{section.label}</h3>
            <p className="text-[10px] text-gray-500">{section.desc}</p>
            <textarea
              value={promptConfig[section.key]}
              onChange={(e) => setPromptConfig((prev) => ({ ...prev, [section.key]: e.target.value }))}
              placeholder="留空使用内置默认值..."
              className="w-full h-32 bg-black/30 border border-white/10 rounded-lg p-3 text-xs text-gray-300 resize-y focus:outline-none focus:border-purple-500/50 font-mono placeholder-gray-600"
            />
          </div>
        ))}

        <div className="flex justify-end">
          <button
            onClick={handleSavePromptDefaults}
            className="px-6 py-2 text-sm font-medium bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors flex items-center gap-2"
          >
            <Save size={16} />
            保存默认值
          </button>
        </div>
      </section>

      <div className="pb-8" />
    </div>
  );
}
