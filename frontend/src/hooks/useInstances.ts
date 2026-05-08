"use client";

import { useCallback, useEffect, useState } from "react";
import {
    instances as instancesApi,
    type InstanceTypeId,
    type ModelInstanceCreate,
    type ModelInstanceOut,
    type ModelInstanceUpdate,
} from "@/lib/api";

export interface InstancesState {
    instances: ModelInstanceOut[];
    loading: boolean;
    error: string | null;
    reload: () => Promise<void>;
    create: (payload: ModelInstanceCreate) => Promise<ModelInstanceOut>;
    update: (id: string, payload: ModelInstanceUpdate) => Promise<ModelInstanceOut>;
    remove: (id: string) => Promise<void>;
    setDefault: (id: string) => Promise<ModelInstanceOut>;
}

/**
 * One-stop hook for managing the user's ModelInstance list.
 *
 * Optimistic-update style for set-default + delete so the UI reflects the
 * change immediately and reconciles after the server round-trip. Pass a
 * ``type`` to filter; omit to load every type at once.
 */
export function useInstances(type?: InstanceTypeId): InstancesState {
    const [list, setList] = useState<ModelInstanceOut[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const reload = useCallback(async () => {
        setLoading(true);
        try {
            const data = await instancesApi.list(type);
            setList(data);
            setError(null);
        } catch (err) {
            setError(err instanceof Error ? err.message : String(err));
        } finally {
            setLoading(false);
        }
    }, [type]);

    useEffect(() => {
        let alive = true;
        instancesApi
            .list(type)
            .then((d) => alive && setList(d))
            .catch((err) => alive && setError(err instanceof Error ? err.message : String(err)))
            .finally(() => alive && setLoading(false));
        return () => {
            alive = false;
        };
    }, [type]);

    const create = useCallback(async (payload: ModelInstanceCreate) => {
        const created = await instancesApi.create(payload);
        setList((curr) => [...curr, created]);
        return created;
    }, []);

    const update = useCallback(async (id: string, payload: ModelInstanceUpdate) => {
        const updated = await instancesApi.update(id, payload);
        setList((curr) => curr.map((i) => (i.id === id ? updated : i)));
        return updated;
    }, []);

    const remove = useCallback(async (id: string) => {
        await instancesApi.delete(id);
        setList((curr) => curr.filter((i) => i.id !== id));
    }, []);

    const setDefault = useCallback(async (id: string) => {
        const updated = await instancesApi.setDefault(id);
        // Demote previous default of same type, promote this one.
        setList((curr) =>
            curr.map((i) => {
                if (i.id === updated.id) return updated;
                if (i.instance_type === updated.instance_type) return { ...i, is_default: false };
                return i;
            }),
        );
        return updated;
    }, []);

    return { instances: list, loading, error, reload, create, update, remove, setDefault };
}
