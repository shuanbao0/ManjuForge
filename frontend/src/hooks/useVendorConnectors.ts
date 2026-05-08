"use client";

import { useEffect, useState } from "react";
import { registry, type VendorConnectorDTO, type ModelCapability } from "@/lib/api";

let cachedPromise: Promise<{ connectors: VendorConnectorDTO[] }> | null = null;

function fetchOnce() {
    if (!cachedPromise) {
        cachedPromise = registry.getVendors().catch((err) => {
            cachedPromise = null;
            throw err;
        });
    }
    return cachedPromise;
}

export function invalidateVendorConnectors() {
    cachedPromise = null;
}

export interface VendorConnectorsState {
    connectors: VendorConnectorDTO[];
    loading: boolean;
    error: string | null;
}

const FALLBACK: VendorConnectorDTO[] = [];

/**
 * Fetch the canonical vendor connector list (DashScope / Kling / Vidu / ...).
 * The Settings UI renders one VendorCard per connector — adding a new vendor
 * to ``src/utils/vendor_connectors.py`` flows through automatically.
 */
export function useVendorConnectors(capability?: ModelCapability): VendorConnectorsState {
    const [state, setState] = useState<VendorConnectorsState>({
        connectors: FALLBACK,
        loading: true,
        error: null,
    });

    useEffect(() => {
        let alive = true;
        fetchOnce()
            .then((res) => {
                if (!alive) return;
                const connectors = capability
                    ? res.connectors.filter((c) => c.capabilities.includes(capability))
                    : res.connectors;
                setState({ connectors, loading: false, error: null });
            })
            .catch((err: unknown) => {
                if (!alive) return;
                setState({
                    connectors: FALLBACK,
                    loading: false,
                    error: err instanceof Error ? err.message : String(err),
                });
            });
        return () => {
            alive = false;
        };
    }, [capability]);

    return state;
}
