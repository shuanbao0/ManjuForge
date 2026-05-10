"use client";

import { useMemo } from "react";
import { useInstances } from "./useInstances";
import type { ModelInstanceOut } from "@/lib/api";
import { resolveI2VFamily, type I2VFamily } from "@/lib/i2vFamilies";

/**
 * A ``ModelInstance`` that has been adapted with the family metadata the UI
 * needs (badge color, capability schema, R2V eligibility). The family is
 * resolved from ``model_name`` at render time, so users editing the instance
 * in Settings (e.g. switching from ``wan2.6-i2v`` → ``kling-v3``) will see
 * the picker re-categorize automatically without a round-trip.
 */
export interface EnrichedInstance extends ModelInstanceOut {
    family: I2VFamily | null;
    /** ``true`` when the instance is selectable under R2V mode (Wan 2.6 only today). */
    r2vEligible: boolean;
}

export interface UseI2VInstancesOptions {
    /** When ``true``, ``r2vEligible`` is forced false for non-Wan-2.6 entries. */
    r2vOnly?: boolean;
}

export interface UseI2VInstancesResult {
    instances: EnrichedInstance[];
    /** First ``is_default`` entry (or ``null`` if no I2V instance configured). */
    defaultInstance: EnrichedInstance | null;
    loading: boolean;
    error: string | null;
    reload: () => Promise<void>;
}

/**
 * Read-only view over the user's I2V instance list, enriched with family
 * metadata for the picker UI. Ordering: default first, then by family
 * registry order, then by ``display_name``.
 */
export function useI2VInstances(opts: UseI2VInstancesOptions = {}): UseI2VInstancesResult {
    const { instances, loading, error, reload } = useInstances("i2v");

    const enriched = useMemo<EnrichedInstance[]>(() => {
        const adapted = instances.map((inst): EnrichedInstance => {
            const family = resolveI2VFamily(inst.model_name);
            return {
                ...inst,
                family,
                r2vEligible: family?.supportsR2V ?? false,
            };
        });
        // Sort: default first → family display order → display_name
        const familyOrder = new Map<string, number>();
        adapted.forEach((i) => {
            if (i.family && !familyOrder.has(i.family.id)) {
                familyOrder.set(i.family.id, familyOrder.size);
            }
        });
        return adapted.sort((a, b) => {
            if (a.is_default !== b.is_default) return a.is_default ? -1 : 1;
            const ao = a.family ? familyOrder.get(a.family.id) ?? 999 : 999;
            const bo = b.family ? familyOrder.get(b.family.id) ?? 999 : 999;
            if (ao !== bo) return ao - bo;
            return a.display_name.localeCompare(b.display_name);
        });
    }, [instances]);

    const defaultInstance = useMemo(
        () => enriched.find((i) => i.is_default) ?? enriched[0] ?? null,
        [enriched],
    );

    // ``r2vOnly`` is exposed via the ``r2vEligible`` flag rather than filtered
    // out — the picker greys the ineligible entries instead of hiding them so
    // the user knows why they can't pick Kling/Vidu in R2V mode.
    void opts.r2vOnly;

    return { instances: enriched, defaultInstance, loading, error, reload };
}
