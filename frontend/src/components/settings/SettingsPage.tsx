"use client";

import { useEffect, useState } from "react";
import {
  Save, Loader2, Key, ChevronDown, ChevronRight, Settings, MessageSquareCode,
  Cpu, Database, ShieldCheck, Image, Video, Layout, Check, User as UserIcon, Building, Box,
} from "lucide-react";
import { me as meApi } from "@/lib/api";
import { T2I_MODELS, I2I_MODELS, I2V_MODELS, ASPECT_RATIOS } from "@/store/projectStore";

// ── Types ────────────────────────────────────────────────────────────────

type ProviderMode = "dashscope" | "vendor";
type LLMProvider = "dashscope" | "openai";
type StorageProvider = "local_only" | "minio" | "aliyun_oss";

interface MyCreds {
  // LLM
  LLM_PROVIDER: LLMProvider;
  DASHSCOPE_API_KEY: string;
  OPENAI_API_KEY: string;
  OPENAI_BASE_URL: string;
  OPENAI_MODEL: string;
  // Provider routing
  KLING_PROVIDER_MODE: ProviderMode;
  KLING_ACCESS_KEY: string;
  KLING_SECRET_KEY: string;
  VIDU_PROVIDER_MODE: ProviderMode;
  VIDU_API_KEY: string;
  PIXVERSE_PROVIDER_MODE: ProviderMode;
  // Endpoint overrides
  DASHSCOPE_BASE_URL: string;
  KLING_BASE_URL: string;
  VIDU_BASE_URL: string;
  // Object storage
  STORAGE_PROVIDER: StorageProvider;
  STORAGE_ENDPOINT: string;
  STORAGE_REGION: string;
  STORAGE_ACCESS_KEY: string;
  STORAGE_SECRET_KEY: string;
  STORAGE_BUCKET: string;
  STORAGE_PATH_PREFIX: string;
}

const DEFAULT_CREDS: MyCreds = {
  LLM_PROVIDER: "dashscope",
  DASHSCOPE_API_KEY: "",
  OPENAI_API_KEY: "",
  OPENAI_BASE_URL: "",
  OPENAI_MODEL: "",
  KLING_PROVIDER_MODE: "dashscope",
  KLING_ACCESS_KEY: "",
  KLING_SECRET_KEY: "",
  VIDU_PROVIDER_MODE: "dashscope",
  VIDU_API_KEY: "",
  PIXVERSE_PROVIDER_MODE: "dashscope",
  DASHSCOPE_BASE_URL: "",
  KLING_BASE_URL: "",
  VIDU_BASE_URL: "",
  STORAGE_PROVIDER: "local_only",
  STORAGE_ENDPOINT: "",
  STORAGE_REGION: "",
  STORAGE_ACCESS_KEY: "",
  STORAGE_SECRET_KEY: "",
  STORAGE_BUCKET: "",
  STORAGE_PATH_PREFIX: "",
};

const PROVIDER_MODE = (v?: string): ProviderMode => (v === "vendor" ? "vendor" : "dashscope");
const LLM_MODE = (v?: string): LLMProvider => (v === "openai" ? "openai" : "dashscope");
const STORAGE_MODE = (v?: string): StorageProvider =>
  v === "minio" ? "minio" : v === "aliyun_oss" ? "aliyun_oss" : "local_only";

const merge = (base: MyCreds, raw: Record<string, string>): MyCreds => ({
  ...base,
  ...raw,
  LLM_PROVIDER: LLM_MODE(raw.LLM_PROVIDER ?? base.LLM_PROVIDER),
  KLING_PROVIDER_MODE: PROVIDER_MODE(raw.KLING_PROVIDER_MODE ?? base.KLING_PROVIDER_MODE),
  VIDU_PROVIDER_MODE: PROVIDER_MODE(raw.VIDU_PROVIDER_MODE ?? base.VIDU_PROVIDER_MODE),
  PIXVERSE_PROVIDER_MODE: PROVIDER_MODE(raw.PIXVERSE_PROVIDER_MODE ?? base.PIXVERSE_PROVIDER_MODE),
  STORAGE_PROVIDER: STORAGE_MODE(raw.STORAGE_PROVIDER ?? base.STORAGE_PROVIDER),
});

const validate = (c: MyCreds): string[] => {
  const errs: string[] = [];
  if (c.LLM_PROVIDER === "dashscope" && !c.DASHSCOPE_API_KEY) errs.push("DashScope API Key");
  if (c.LLM_PROVIDER === "openai" && !c.OPENAI_API_KEY) errs.push("OpenAI API Key");
  if (c.KLING_PROVIDER_MODE === "vendor") {
    if (!c.KLING_ACCESS_KEY) errs.push("Kling Access Key");
    if (!c.KLING_SECRET_KEY) errs.push("Kling Secret Key");
  }
  if (c.VIDU_PROVIDER_MODE === "vendor" && !c.VIDU_API_KEY) errs.push("Vidu API Key");
  if (c.STORAGE_PROVIDER !== "local_only") {
    if (!c.STORAGE_ENDPOINT) errs.push("Storage Endpoint");
    if (!c.STORAGE_ACCESS_KEY) errs.push("Storage Access Key");
    if (!c.STORAGE_SECRET_KEY) errs.push("Storage Secret Key");
    if (!c.STORAGE_BUCKET) errs.push("Storage Bucket");
  }
  return errs;
};

// ── Local UI prefs (kept in localStorage, per-browser, not per-user) ─────

const LS_KEY_MODEL = "manju_forge_default_model_settings";
const LS_KEY_PROMPT = "manju_forge_default_prompt_config";

interface DefaultModelSettings {
  t2i_model: string;
  i2i_model: string;
  i2v_model: string;
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

// ── Component ────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const [creds, setCreds] = useState<MyCreds>(DEFAULT_CREDS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [endpointsOpen, setEndpointsOpen] = useState(false);

  const [modelSettings, setModelSettings] = useState<DefaultModelSettings>(() =>
    loadFromLS(LS_KEY_MODEL, {
      t2i_model: "wan2.5-t2i-preview",
      i2i_model: "wan2.5-i2i-preview",
      i2v_model: "wan2.5-i2v-preview",
      character_aspect_ratio: "9:16",
      scene_aspect_ratio: "16:9",
      prop_aspect_ratio: "1:1",
      storyboard_aspect_ratio: "16:9",
    })
  );

  const [promptConfig, setPromptConfig] = useState<DefaultPromptConfig>(() =>
    loadFromLS(LS_KEY_PROMPT, { storyboard_polish: "", video_polish: "", r2v_polish: "" })
  );

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setLoadError(null);
    // We pull the *unmasked* values into the editor so users can see what
    // they have configured. The endpoint requires authentication so this
    // never leaks across users.
    meApi
      .getCredentials(true)
      .then((res) => {
        if (alive) setCreds((prev) => merge(prev, res.values || {}));
      })
      .catch(() => {
        if (alive) setLoadError("无法加载我的密钥。后端是否在运行？");
      })
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const handleChange = <K extends keyof MyCreds>(key: K, value: MyCreds[K]) => {
    setCreds((prev) => ({ ...prev, [key]: value }));
  };

  const handleSave = async () => {
    const errs = validate(creds);
    if (errs.length > 0) {
      alert(`请填写必填字段：\n- ${errs.join("\n- ")}`);
      return;
    }
    setSaving(true);
    try {
      await meApi.replaceCredentials(creds as unknown as Record<string, string>);
      alert("已保存");
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: { message?: string } } } })?.response?.data?.detail?.message ?? "保存失败";
      alert(msg);
    } finally {
      setSaving(false);
    }
  };

  const handleSaveModelDefaults = () => {
    localStorage.setItem(LS_KEY_MODEL, JSON.stringify(modelSettings));
    alert("默认模型设置已保存");
  };
  const handleSavePromptDefaults = () => {
    localStorage.setItem(LS_KEY_PROMPT, JSON.stringify(promptConfig));
    alert("默认 prompt 已保存");
  };

  const inputClass =
    "w-full bg-black/30 border border-white/10 rounded-lg px-4 py-2 text-white placeholder-gray-500 focus:outline-none focus:border-primary/50 transition-colors";
  const modeButton = (active: boolean) =>
    `px-3 py-1.5 text-xs rounded-md border transition-colors ${active ? "border-amber-500/60 bg-amber-500/15 text-amber-200" : "border-white/10 bg-white/5 text-gray-400 hover:text-gray-200"}`;

  return (
    <div className="container mx-auto px-6 py-8 max-w-4xl space-y-8">
      <div className="flex items-center gap-3">
        <div className="p-2 bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-lg">
          <ShieldCheck size={20} className="text-amber-400" />
        </div>
        <div>
          <h1 className="text-2xl font-display font-bold text-white">设置</h1>
          <p className="text-xs text-gray-500">所有密钥与对象存储凭证仅对你可见，加密存储于服务器侧</p>
        </div>
      </div>

      {/* ── My credentials ── */}
      <section className="glass-panel rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-amber-500/20 to-orange-500/20 rounded-lg">
            <Key size={20} className="text-amber-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">我的密钥</h2>
            <p className="text-xs text-gray-500">DashScope-first，可选切换到 OpenAI 兼容；可选 Kling/Vidu 直连</p>
          </div>
        </div>

        {loading ? (
          <div className="flex items-center justify-center py-12 text-gray-400">
            <Loader2 size={24} className="animate-spin text-amber-400" />
            <span className="ml-2 text-sm">加载中…</span>
          </div>
        ) : loadError ? (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-sm text-red-300">{loadError}</div>
        ) : (
          <>
            {/* DashScope */}
            <div>
              <label className="flex items-center justify-between text-sm font-medium text-gray-300 mb-2">
                <span>DashScope API Key {creds.LLM_PROVIDER === "dashscope" && <span className="text-red-500">*</span>}</span>
                <span className="text-gray-600 font-normal text-xs">e.g. sk-xxx</span>
              </label>
              <input type="password" value={creds.DASHSCOPE_API_KEY} onChange={(e) => handleChange("DASHSCOPE_API_KEY", e.target.value)} placeholder="DashScope-first 默认密钥" className={inputClass} />
            </div>

            {/* LLM Provider */}
            <div className="pt-4 border-t border-white/10">
              <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2"><Cpu size={14} className="text-emerald-400" /> LLM Provider</h3>
              <p className="text-[10px] text-gray-500 mb-4">用于剧本分析和 prompt 润色。默认 DashScope，复用上方 Key</p>
              <div className="bg-white/5 border border-white/10 rounded-lg p-4 space-y-4">
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => handleChange("LLM_PROVIDER", "dashscope")} className={modeButton(creds.LLM_PROVIDER === "dashscope")}>DashScope（默认）</button>
                  <button type="button" onClick={() => handleChange("LLM_PROVIDER", "openai")} className={modeButton(creds.LLM_PROVIDER === "openai")}>OpenAI 兼容</button>
                </div>
                {creds.LLM_PROVIDER === "openai" && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">OpenAI API Key <span className="text-red-500">*</span></label>
                      <input type="password" value={creds.OPENAI_API_KEY} onChange={(e) => handleChange("OPENAI_API_KEY", e.target.value)} placeholder="sk-... 或 ollama" className={inputClass} />
                    </div>
                    <div>
                      <label className="flex items-center justify-between text-sm font-medium text-gray-300 mb-2"><span>OpenAI Base URL</span><span className="text-gray-600 font-normal text-xs">留空则用 https://api.openai.com/v1</span></label>
                      <input type="text" value={creds.OPENAI_BASE_URL} onChange={(e) => handleChange("OPENAI_BASE_URL", e.target.value)} placeholder="https://api.deepseek.com/v1" className={inputClass} />
                    </div>
                    <div>
                      <label className="flex items-center justify-between text-sm font-medium text-gray-300 mb-2"><span>OpenAI Model</span><span className="text-gray-600 font-normal text-xs">e.g. gpt-4o, deepseek-chat</span></label>
                      <input type="text" value={creds.OPENAI_MODEL} onChange={(e) => handleChange("OPENAI_MODEL", e.target.value)} placeholder="gpt-4o" className={inputClass} />
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Kling */}
            <div className="pt-4 border-t border-white/10">
              <h3 className="text-sm font-bold text-white mb-4">Kling Provider</h3>
              <div className="bg-white/5 border border-white/10 rounded-lg p-4 space-y-4">
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => handleChange("KLING_PROVIDER_MODE", "dashscope")} className={modeButton(creds.KLING_PROVIDER_MODE === "dashscope")}>DashScope</button>
                  <button type="button" onClick={() => handleChange("KLING_PROVIDER_MODE", "vendor")} className={modeButton(creds.KLING_PROVIDER_MODE === "vendor")}>Vendor Direct</button>
                </div>
                {creds.KLING_PROVIDER_MODE === "vendor" && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">Kling Access Key <span className="text-red-500">*</span></label>
                      <input type="password" value={creds.KLING_ACCESS_KEY} onChange={(e) => handleChange("KLING_ACCESS_KEY", e.target.value)} placeholder="Kling Access Key" className={inputClass} />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">Kling Secret Key <span className="text-red-500">*</span></label>
                      <input type="password" value={creds.KLING_SECRET_KEY} onChange={(e) => handleChange("KLING_SECRET_KEY", e.target.value)} placeholder="Kling Secret Key" className={inputClass} />
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Vidu */}
            <div className="pt-4 border-t border-white/10">
              <h3 className="text-sm font-bold text-white mb-4">Vidu Provider</h3>
              <div className="bg-white/5 border border-white/10 rounded-lg p-4 space-y-4">
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={() => handleChange("VIDU_PROVIDER_MODE", "dashscope")} className={modeButton(creds.VIDU_PROVIDER_MODE === "dashscope")}>DashScope</button>
                  <button type="button" onClick={() => handleChange("VIDU_PROVIDER_MODE", "vendor")} className={modeButton(creds.VIDU_PROVIDER_MODE === "vendor")}>Vendor Direct</button>
                </div>
                {creds.VIDU_PROVIDER_MODE === "vendor" && (
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Vidu API Key <span className="text-red-500">*</span></label>
                    <input type="password" value={creds.VIDU_API_KEY} onChange={(e) => handleChange("VIDU_API_KEY", e.target.value)} placeholder="Vidu API Key" className={inputClass} />
                  </div>
                )}
              </div>
            </div>

            {/* Object storage */}
            <div className="pt-4 border-t border-white/10">
              <h3 className="text-sm font-bold text-white mb-2 flex items-center gap-2"><Database size={14} className="text-fuchsia-400" /> 对象存储</h3>
              <p className="text-[10px] text-gray-500 mb-4">默认仅本地保存。也可选 MinIO（自建）或 Aliyun OSS（S3 兼容协议）。本地路径仍作为 FFmpeg 工作目录使用</p>
              <div className="bg-white/5 border border-white/10 rounded-lg p-4 space-y-4">
                <div className="flex flex-wrap gap-2">
                  {(["local_only", "minio", "aliyun_oss"] as const).map((p) => (
                    <button key={p} type="button" onClick={() => handleChange("STORAGE_PROVIDER", p)} className={modeButton(creds.STORAGE_PROVIDER === p)}>
                      {p === "local_only" ? "仅本地" : p === "minio" ? "MinIO" : "Aliyun OSS"}
                    </button>
                  ))}
                </div>
                {creds.STORAGE_PROVIDER !== "local_only" && (
                  <>
                    <div>
                      <label className="flex items-center justify-between text-sm font-medium text-gray-300 mb-2"><span>Endpoint <span className="text-red-500">*</span></span><span className="text-gray-600 font-normal text-xs">e.g. https://s3.example.com</span></label>
                      <input type="text" value={creds.STORAGE_ENDPOINT} onChange={(e) => handleChange("STORAGE_ENDPOINT", e.target.value)} placeholder={creds.STORAGE_PROVIDER === "minio" ? "http://minio.local:9000" : "https://oss-cn-beijing.aliyuncs.com"} className={inputClass} />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">Access Key <span className="text-red-500">*</span></label>
                        <input type="password" value={creds.STORAGE_ACCESS_KEY} onChange={(e) => handleChange("STORAGE_ACCESS_KEY", e.target.value)} className={inputClass} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">Secret Key <span className="text-red-500">*</span></label>
                        <input type="password" value={creds.STORAGE_SECRET_KEY} onChange={(e) => handleChange("STORAGE_SECRET_KEY", e.target.value)} className={inputClass} />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">Bucket <span className="text-red-500">*</span></label>
                        <input type="text" value={creds.STORAGE_BUCKET} onChange={(e) => handleChange("STORAGE_BUCKET", e.target.value)} className={inputClass} />
                      </div>
                      <div>
                        <label className="block text-sm font-medium text-gray-300 mb-2">Region</label>
                        <input type="text" value={creds.STORAGE_REGION} onChange={(e) => handleChange("STORAGE_REGION", e.target.value)} placeholder="us-east-1" className={inputClass} />
                      </div>
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-300 mb-2">Path Prefix</label>
                      <input type="text" value={creds.STORAGE_PATH_PREFIX} onChange={(e) => handleChange("STORAGE_PATH_PREFIX", e.target.value)} placeholder="manju-forge" className={inputClass} />
                    </div>
                  </>
                )}
              </div>
            </div>

            {/* Advanced endpoints */}
            <div className="pt-4 border-t border-white/10">
              <button type="button" onClick={() => setEndpointsOpen((v) => !v)} className="flex items-center gap-2 text-sm font-medium text-gray-400 hover:text-gray-200 transition-colors">
                {endpointsOpen ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                高级：API 端点覆盖
              </button>
              {endpointsOpen && (
                <div className="mt-4 space-y-4">
                  <p className="text-xs text-gray-500">自定义提供商 Base URL，留空则使用默认值</p>
                  {[
                    { key: "DASHSCOPE_BASE_URL" as const, label: "DashScope", placeholder: "https://dashscope.aliyuncs.com" },
                    { key: "KLING_BASE_URL" as const, label: "Kling", placeholder: "https://api-beijing.klingai.com/v1" },
                    { key: "VIDU_BASE_URL" as const, label: "Vidu", placeholder: "https://api.vidu.cn/ent/v2" },
                  ].map(({ key, label, placeholder }) => (
                    <div key={key}>
                      <label className="flex items-center justify-between text-sm font-medium text-gray-300 mb-2"><span>{label} Base URL</span><span className="text-gray-600 font-normal text-xs">{placeholder}</span></label>
                      <input type="text" value={creds[key]} onChange={(e) => handleChange(key, e.target.value)} placeholder={placeholder} className={inputClass + " text-sm"} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex justify-end">
              <button onClick={handleSave} disabled={saving || loading} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-amber-600 to-orange-600 hover:from-amber-500 hover:to-orange-500 text-white text-sm font-medium rounded-lg transition-all disabled:opacity-50">
                {saving ? <Loader2 size={16} className="animate-spin" /> : <Save size={16} />}
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          </>
        )}
      </section>

      {/* ── Defaults (browser-local) ── */}
      <section className="glass-panel rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-lg">
            <Settings size={20} className="text-blue-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">默认模型设置</h2>
            <p className="text-xs text-gray-500">为新项目预填的默认值（仅保存在当前浏览器）</p>
          </div>
        </div>

        <div className="space-y-5">
          <div className="flex items-center gap-2 text-sm font-bold text-white"><Image size={16} className="text-green-400" /><span>Text-to-Image</span></div>
          <div className="grid grid-cols-2 gap-2">
            {T2I_MODELS.map((model) => (
              <button key={model.id} onClick={() => setModelSettings((s) => ({ ...s, t2i_model: model.id }))} className={`relative flex flex-col items-start p-3 rounded-lg border transition-all text-left ${modelSettings.t2i_model === model.id ? "border-green-500/50 bg-green-500/10" : "border-white/10 hover:border-white/20 bg-white/5"}`}>
                {modelSettings.t2i_model === model.id && <div className="absolute top-2 right-2"><Check size={14} className="text-green-400" /></div>}
                <span className="text-sm font-medium text-white">{model.name}</span>
                <span className="text-xs text-gray-500">{model.description}</span>
              </button>
            ))}
          </div>

          <div className="grid grid-cols-3 gap-4">
            {([
              { key: "character_aspect_ratio" as const, label: "Character", icon: UserIcon },
              { key: "scene_aspect_ratio" as const, label: "Scene", icon: Building },
              { key: "prop_aspect_ratio" as const, label: "Prop", icon: Box },
            ] as const).map(({ key, label, icon: Icon }) => (
              <div key={key} className="space-y-2">
                <div className="flex items-center gap-1 text-xs text-gray-400"><Icon size={12} /><label>{label}</label></div>
                <div className="space-y-1">
                  {ASPECT_RATIOS.map((ratio) => (
                    <button key={ratio.id} onClick={() => setModelSettings((s) => ({ ...s, [key]: ratio.id }))} className={`w-full flex flex-col items-center py-2 px-2 rounded border transition-all ${modelSettings[key] === ratio.id ? "border-green-500/50 bg-green-500/10" : "border-white/10 hover:border-white/20 bg-white/5"}`}>
                      <span className="text-xs font-medium text-white">{ratio.name}</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-white/10 pt-4">
            <div className="flex items-center gap-2 text-sm font-bold text-white"><Layout size={16} className="text-blue-400" /><span>Storyboard (I2I)</span></div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {I2I_MODELS.map((model) => (
                <button key={model.id} onClick={() => setModelSettings((s) => ({ ...s, i2i_model: model.id }))} className={`relative flex flex-col items-start p-3 rounded-lg border transition-all text-left ${modelSettings.i2i_model === model.id ? "border-blue-500/50 bg-blue-500/10" : "border-white/10 hover:border-white/20 bg-white/5"}`}>
                  {modelSettings.i2i_model === model.id && <div className="absolute top-2 right-2"><Check size={14} className="text-blue-400" /></div>}
                  <span className="text-sm font-medium text-white">{model.name}</span>
                  <span className="text-xs text-gray-500">{model.description}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="border-t border-white/10 pt-4">
            <div className="flex items-center gap-2 text-sm font-bold text-white"><Video size={16} className="text-purple-400" /><span>Motion (I2V)</span></div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {I2V_MODELS.map((model) => (
                <button key={model.id} onClick={() => setModelSettings((s) => ({ ...s, i2v_model: model.id }))} className={`relative flex flex-col items-start p-3 rounded-lg border transition-all text-left ${modelSettings.i2v_model === model.id ? "border-purple-500/50 bg-purple-500/10" : "border-white/10 hover:border-white/20 bg-white/5"}`}>
                  {modelSettings.i2v_model === model.id && <div className="absolute top-2 right-2"><Check size={14} className="text-purple-400" /></div>}
                  <span className="text-sm font-medium text-white">{model.name}</span>
                  <span className="text-xs text-gray-500">{model.description}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="flex justify-end">
          <button onClick={handleSaveModelDefaults} className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white text-sm font-medium rounded-lg transition-all">
            <Save size={16} />
            保存默认值
          </button>
        </div>
      </section>

      <section className="glass-panel rounded-xl p-6 space-y-6">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-purple-500/20 rounded-lg">
            <MessageSquareCode size={20} className="text-purple-400" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">默认提示词配置</h2>
            <p className="text-xs text-gray-500">为新项目预填的系统 prompt（留空使用内置默认值）</p>
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
          <button onClick={handleSavePromptDefaults} className="px-6 py-2 text-sm font-medium bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors flex items-center gap-2">
            <Save size={16} />
            保存默认值
          </button>
        </div>
      </section>

      <div className="pb-8" />
    </div>
  );
}
