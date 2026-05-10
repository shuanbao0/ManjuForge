/**
 * I2V Family Capability Registry.
 *
 * Mirrors the backend ``provider_registry.py`` "model family" concept on the
 * frontend so the UI can decide *which controls to render* once a user picks
 * a ``ModelInstance``. Identity (vendor/credentials/model_name) lives on the
 * instance; capabilities live here.
 *
 * Each family is a pure record + a ``matches(modelName)`` predicate. Resolve
 * via :func:`resolveI2VFamily`. New vendors only need: append a family entry.
 */

export type DurationConfig =
  | { type: "slider"; min: number; max: number; step: number; default: number }
  | { type: "buttons"; options: number[]; default: number }
  | { type: "fixed"; value: number };

export interface ModelParamSupport {
  resolution?: { options: string[]; default: string };
  seed?: boolean;
  negativePrompt?: boolean;
  promptExtend?: boolean;
  shotType?: boolean;
  audio?: boolean;
  // Kling
  mode?: { options: string[]; default: string };
  sound?: boolean;
  cfgScale?: { min: number; max: number; step: number; default: number };
  // Vidu
  viduAudio?: boolean;
  movementAmplitude?: { options: string[]; default: string };
}

export type I2VFamilyId =
  | "wan2.6"
  | "wan2.5"
  | "wan2.2"
  | "kling"
  | "vidu"
  | "pixverse";

export interface I2VFamily {
  id: I2VFamilyId;
  /** Human-readable name shown on the family badge. */
  displayName: string;
  /** Tailwind-friendly accent color class for the vendor dot / badge. */
  accent: string;
  /** Returns true when this family owns the given ``model_name``. */
  matches: (modelName: string) => boolean;
  duration: DurationConfig;
  params: ModelParamSupport;
  /** Whether this family may be selected when ``generation_mode === "r2v"``. */
  supportsR2V: boolean;
  /** Fallback model_name used when the user has no instance configured yet. */
  fallbackModelName: string;
}

const WAN26_PARAMS: ModelParamSupport = {
  resolution: { options: ["480p", "720p", "1080p"], default: "720p" },
  seed: true,
  negativePrompt: true,
  promptExtend: true,
  shotType: true,
  audio: true,
};

const WAN25_PARAMS: ModelParamSupport = {
  resolution: { options: ["480p", "720p", "1080p"], default: "720p" },
  seed: true,
  negativePrompt: true,
  audio: true,
};

const WAN22_PARAMS: ModelParamSupport = {
  resolution: { options: ["480p", "720p", "1080p"], default: "720p" },
  seed: true,
  negativePrompt: true,
};

const KLING_PARAMS: ModelParamSupport = {
  negativePrompt: true,
  mode: { options: ["std", "pro"], default: "std" },
  sound: true,
  cfgScale: { min: 0, max: 1, step: 0.1, default: 0.5 },
};

const VIDU_PARAMS: ModelParamSupport = {
  resolution: { options: ["540p", "720p", "1080p"], default: "720p" },
  seed: true,
  viduAudio: true,
  movementAmplitude: {
    options: ["auto", "small", "medium", "large"],
    default: "auto",
  },
};

const PIXVERSE_PARAMS: ModelParamSupport = {
  resolution: { options: ["480p", "720p", "1080p"], default: "720p" },
  seed: true,
  negativePrompt: true,
};

/**
 * The single source of truth for I2V capabilities. Order = display priority
 * (used as a stable secondary sort when grouping instances by family).
 */
export const I2V_FAMILIES: readonly I2VFamily[] = [
  {
    id: "wan2.6",
    displayName: "Wan 2.6",
    accent: "bg-blue-500",
    matches: (m) => m.startsWith("wan2.6"),
    duration: { type: "slider", min: 2, max: 15, step: 1, default: 5 },
    params: WAN26_PARAMS,
    supportsR2V: true,
    fallbackModelName: "wan2.6-i2v",
  },
  {
    id: "wan2.5",
    displayName: "Wan 2.5",
    accent: "bg-sky-500",
    matches: (m) => m.startsWith("wan2.5"),
    duration: { type: "buttons", options: [5, 10], default: 5 },
    params: WAN25_PARAMS,
    supportsR2V: false,
    fallbackModelName: "wan2.5-i2v-preview",
  },
  {
    id: "wan2.2",
    displayName: "Wan 2.2",
    accent: "bg-cyan-500",
    matches: (m) => m.startsWith("wan2.2"),
    duration: { type: "fixed", value: 5 },
    params: WAN22_PARAMS,
    supportsR2V: false,
    fallbackModelName: "wan2.2-i2v-plus",
  },
  {
    id: "kling",
    displayName: "Kling",
    accent: "bg-purple-500",
    matches: (m) => m.startsWith("kling"),
    duration: { type: "slider", min: 3, max: 15, step: 1, default: 5 },
    params: KLING_PARAMS,
    supportsR2V: false,
    fallbackModelName: "kling-v3",
  },
  {
    id: "vidu",
    displayName: "Vidu",
    accent: "bg-orange-500",
    matches: (m) => m.startsWith("vidu"),
    duration: { type: "slider", min: 1, max: 16, step: 1, default: 5 },
    params: VIDU_PARAMS,
    supportsR2V: false,
    fallbackModelName: "viduq3-pro",
  },
  {
    id: "pixverse",
    displayName: "Pixverse",
    accent: "bg-pink-500",
    matches: (m) => m.startsWith("pixverse"),
    duration: { type: "buttons", options: [5, 8], default: 5 },
    params: PIXVERSE_PARAMS,
    supportsR2V: false,
    fallbackModelName: "pixverse-v4",
  },
] as const;

/** Look up the family that owns ``modelName``. Returns ``null`` for unknown. */
export function resolveI2VFamily(modelName: string | null | undefined): I2VFamily | null {
  if (!modelName) return null;
  return I2V_FAMILIES.find((f) => f.matches(modelName)) ?? null;
}

/** Same as ``resolveI2VFamily`` but falls back to Wan 2.6 for unknown names. */
export function resolveI2VFamilyOrDefault(modelName: string | null | undefined): I2VFamily {
  return resolveI2VFamily(modelName) ?? I2V_FAMILIES[0];
}

export interface FamilyFilter {
  /** When ``true``, only return families whose ``supportsR2V`` is ``true``. */
  r2vOnly?: boolean;
}

export function listFamilies(filter: FamilyFilter = {}): I2VFamily[] {
  return I2V_FAMILIES.filter((f) => !filter.r2vOnly || f.supportsR2V);
}

/**
 * Clamp ``value`` into the family's allowed duration range. Used when the
 * user switches families and the previously-chosen duration is no longer valid.
 */
export function clampDuration(family: I2VFamily, value: number): number {
  const d = family.duration;
  if (d.type === "fixed") return d.value;
  if (d.type === "slider") {
    if (value < d.min || value > d.max) return d.default;
    return value;
  }
  // buttons
  return d.options.includes(value) ? value : d.default;
}

/**
 * Default values when switching family — used by the picker to reset
 * model-specific params (kling cfg_scale / vidu amplitude / shot_type / ...).
 */
export interface FamilyDefaults {
  duration: number;
  resolution: string;
  promptExtend: boolean;
  negativePrompt: string;
  shotType: string;
  generateAudio: boolean;
  audioUrl: string;
  mode: string;
  sound: boolean;
  cfgScale: number;
  viduAudio: boolean;
  movementAmplitude: string;
}

export function familyDefaults(family: I2VFamily): FamilyDefaults {
  const d = family.duration;
  const defaultDuration =
    d.type === "fixed" ? d.value : d.type === "slider" ? d.default : d.default;
  const p = family.params;
  return {
    duration: defaultDuration,
    resolution: p.resolution?.default ?? "720p",
    promptExtend: !!p.promptExtend,
    negativePrompt: "",
    shotType: "single",
    generateAudio: false,
    audioUrl: "",
    mode: p.mode?.default ?? "std",
    sound: false,
    cfgScale: p.cfgScale?.default ?? 0.5,
    viduAudio: true,
    movementAmplitude: p.movementAmplitude?.default ?? "auto",
  };
}

/** Tailwind grid-cols class used by buttons-style duration controls. */
export const GRID_COLS_CLASS: Record<number, string> = {
  2: "grid-cols-2",
  3: "grid-cols-3",
  4: "grid-cols-4",
  5: "grid-cols-5",
};
