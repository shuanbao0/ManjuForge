"use client";

import { useEffect, useState } from "react";
import {
    registry,
    type ModelCardDTO,
    type LLMPresetDTO,
    type AspectRatioDTO,
    type ModelCapability,
    type ModelCatalogDTO,
} from "@/lib/api";
import {
    T2I_MODELS as FALLBACK_T2I,
    I2I_MODELS as FALLBACK_I2I,
    I2V_MODELS as FALLBACK_I2V,
    ASPECT_RATIOS as FALLBACK_ASPECT_RATIOS,
} from "@/store/projectStore";

// ─────────────────────────────────────────────────────────────────────────
// Why this hook?
//
// The legacy `T2I_MODELS` / `I2I_MODELS` / `I2V_MODELS` arrays in
// `projectStore.ts` were the single hardcoded source. Every time the team
// added a model, both the backend (provider routing) AND the frontend
// (display dropdown) had to be edited in lockstep, which drifted in practice.
//
// Now the backend `/registry/models` endpoint is canonical. This hook fetches
// it once per mount and caches the response in module state so subsequent
// callers reuse it. The hardcoded arrays still live in `projectStore.ts` so
// the UI renders something reasonable on first paint / when offline.
//
// Adding a new model = one entry in `src/utils/model_catalog.py`. Done.
// ─────────────────────────────────────────────────────────────────────────

let cachedPromise: Promise<ModelCatalogDTO> | null = null;

function fetchOnce(): Promise<ModelCatalogDTO> {
    if (!cachedPromise) {
        cachedPromise = registry.getCatalog().catch((err) => {
            // Reset on failure so the next consumer retries instead of being
            // stuck with a rejected promise forever.
            cachedPromise = null;
            throw err;
        });
    }
    return cachedPromise;
}

/** Reset the in-memory cache (useful after admin updates the registry). */
export function invalidateModelCatalog() {
    cachedPromise = null;
}

export interface ModelCatalogState {
    cards: ModelCardDTO[];
    presets: LLMPresetDTO[];
    aspectRatios: AspectRatioDTO[];
    loading: boolean;
    error: string | null;
}

const FALLBACK_CARDS: ModelCardDTO[] = [
    ...FALLBACK_T2I.map(legacyToCard("t2i")),
    ...FALLBACK_I2I.map(legacyToCard("i2i")),
    ...FALLBACK_I2V.map((m) => legacyToCard("i2v")(m)),
];

const FALLBACK_ASPECT: AspectRatioDTO[] = FALLBACK_ASPECT_RATIOS.map((r) => ({
    id: r.id,
    name: r.name,
    description: r.description,
}));

function legacyToCard(capability: ModelCapability) {
    return (m: { id: string; name: string; description: string }): ModelCardDTO => ({
        id: m.id,
        family: m.id.split(/[-]/)[0],
        display_name: m.name,
        description: m.description,
        capabilities: [capability],
        provider_key: "DASHSCOPE",
        requires_credentials: ["DASHSCOPE_API_KEY"],
        available: true,
        badges: [],
    });
}

/**
 * Fetch the full model catalog with stable fallbacks.
 *
 * Returns immediately with hardcoded fallbacks so consumers can render
 * dropdowns without waiting; replaces them once the backend response lands.
 */
export function useModelCatalog(): ModelCatalogState {
    const [state, setState] = useState<ModelCatalogState>({
        cards: FALLBACK_CARDS,
        presets: [],
        aspectRatios: FALLBACK_ASPECT,
        loading: true,
        error: null,
    });

    useEffect(() => {
        let alive = true;
        fetchOnce()
            .then((catalog) => {
                if (!alive) return;
                setState({
                    cards: catalog.cards,
                    presets: catalog.presets,
                    aspectRatios: catalog.aspect_ratios.length ? catalog.aspect_ratios : FALLBACK_ASPECT,
                    loading: false,
                    error: null,
                });
            })
            .catch((err: unknown) => {
                if (!alive) return;
                setState((s) => ({
                    ...s,
                    loading: false,
                    error: err instanceof Error ? err.message : String(err),
                }));
            });
        return () => {
            alive = false;
        };
    }, []);

    return state;
}

/** Filter the catalog by a single capability (t2i / i2i / i2v / ...). */
export function useModelsByCapability(capability: ModelCapability) {
    const { cards, loading, error } = useModelCatalog();
    return {
        models: cards.filter((c) => c.capabilities.includes(capability)),
        loading,
        error,
    };
}
