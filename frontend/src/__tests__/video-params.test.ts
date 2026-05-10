/**
 * Tests for the I2V family capability registry.
 *
 * Covers:
 * - Family registry completeness + uniqueness
 * - Per-family ModelParamSupport correctness
 * - resolveI2VFamily() prefix matching + fallback semantics
 * - clampDuration() invariants per duration type
 * - familyDefaults() reset values
 * - GRID_COLS_CLASS coverage of widths actually emitted by the registry
 */
import { describe, it, expect } from 'vitest';
import {
    I2V_FAMILIES,
    GRID_COLS_CLASS,
    resolveI2VFamily,
    resolveI2VFamilyOrDefault,
    listFamilies,
    clampDuration,
    familyDefaults,
    type I2VFamily,
} from '@/lib/i2vFamilies';

// ── Registry shape ────────────────────────────────────────────────────────

describe('I2V_FAMILIES registry', () => {
    it('每个 family 都包含 params + duration + matches', () => {
        for (const f of I2V_FAMILIES) {
            expect(f.params).toBeDefined();
            expect(f.duration).toBeDefined();
            expect(['slider', 'buttons', 'fixed']).toContain(f.duration.type);
            expect(typeof f.matches).toBe('function');
            expect(typeof f.fallbackModelName).toBe('string');
        }
    });

    it('family id 唯一', () => {
        const ids = I2V_FAMILIES.map((f) => f.id);
        expect(new Set(ids).size).toBe(ids.length);
    });

    it('每个 family 的 fallbackModelName 都能被自己的 matches 命中', () => {
        for (const f of I2V_FAMILIES) {
            expect(f.matches(f.fallbackModelName)).toBe(true);
        }
    });
});

// ── resolveI2VFamily — prefix matching ────────────────────────────────────

describe('resolveI2VFamily', () => {
    it('Wan 2.6 prefix → wan2.6 family', () => {
        expect(resolveI2VFamily('wan2.6-i2v')?.id).toBe('wan2.6');
        expect(resolveI2VFamily('wan2.6-i2v-flash')?.id).toBe('wan2.6');
        expect(resolveI2VFamily('wan2.6-r2v')?.id).toBe('wan2.6');
    });

    it('Kling prefix → kling family', () => {
        expect(resolveI2VFamily('kling-v3')?.id).toBe('kling');
        expect(resolveI2VFamily('kling-2.1-master')?.id).toBe('kling');
    });

    it('Vidu prefix → vidu family', () => {
        expect(resolveI2VFamily('viduq3-pro')?.id).toBe('vidu');
        expect(resolveI2VFamily('viduq3-turbo')?.id).toBe('vidu');
    });

    it('未知 model_name 返回 null', () => {
        expect(resolveI2VFamily('totally-made-up-model')).toBeNull();
        expect(resolveI2VFamily('')).toBeNull();
        expect(resolveI2VFamily(null)).toBeNull();
        expect(resolveI2VFamily(undefined)).toBeNull();
    });

    it('resolveI2VFamilyOrDefault 未知名时回落到 wan2.6', () => {
        expect(resolveI2VFamilyOrDefault('totally-made-up-model').id).toBe('wan2.6');
        expect(resolveI2VFamilyOrDefault(null).id).toBe('wan2.6');
    });
});

// ── listFamilies — R2V filter ──────────────────────────────────────────────

describe('listFamilies', () => {
    it('默认返回全部', () => {
        expect(listFamilies()).toHaveLength(I2V_FAMILIES.length);
    });

    it('r2vOnly=true 仅保留 supportsR2V 的 family', () => {
        const r2v = listFamilies({ r2vOnly: true });
        expect(r2v.every((f) => f.supportsR2V)).toBe(true);
        expect(r2v.map((f) => f.id)).toContain('wan2.6');
    });
});

// ── Per-family capabilities ────────────────────────────────────────────────

function familyById(id: I2VFamily['id']): I2VFamily {
    const f = I2V_FAMILIES.find((x) => x.id === id);
    if (!f) throw new Error(`missing family ${id}`);
    return f;
}

describe('Wan 2.6 capability', () => {
    const f = familyById('wan2.6');

    it('支持完整 Wan 参数集 + 480/720/1080 分辨率', () => {
        expect(f.params.seed).toBe(true);
        expect(f.params.negativePrompt).toBe(true);
        expect(f.params.promptExtend).toBe(true);
        expect(f.params.shotType).toBe(true);
        expect(f.params.audio).toBe(true);
        expect(f.params.resolution!.options).toEqual(['480p', '720p', '1080p']);
        expect(f.params.resolution!.default).toBe('720p');
    });

    it('唯一支持 R2V', () => {
        expect(f.supportsR2V).toBe(true);
    });
});

describe('Kling capability', () => {
    const f = familyById('kling');

    it('支持 mode/sound/cfgScale，不支持 Wan 独有参数', () => {
        expect(f.params.mode!.options).toEqual(['std', 'pro']);
        expect(f.params.mode!.default).toBe('std');
        expect(f.params.cfgScale).toEqual({ min: 0, max: 1, step: 0.1, default: 0.5 });
        expect(f.params.sound).toBe(true);
        expect(f.params.resolution).toBeUndefined();
        expect(f.params.promptExtend).toBeUndefined();
    });

    it('R2V 不可用', () => {
        expect(f.supportsR2V).toBe(false);
    });
});

describe('Vidu capability', () => {
    const f = familyById('vidu');

    it('支持 viduAudio + movementAmplitude，540p 起步', () => {
        expect(f.params.viduAudio).toBe(true);
        expect(f.params.movementAmplitude!.options).toEqual([
            'auto', 'small', 'medium', 'large',
        ]);
        expect(f.params.resolution!.options).toEqual(['540p', '720p', '1080p']);
    });

    it('不支持 Kling/Wan 独有参数', () => {
        expect(f.params.mode).toBeUndefined();
        expect(f.params.cfgScale).toBeUndefined();
        expect(f.params.promptExtend).toBeUndefined();
        expect(f.params.shotType).toBeUndefined();
    });
});

// ── clampDuration ─────────────────────────────────────────────────────────

describe('clampDuration', () => {
    it('fixed: 永远返回 fixed value', () => {
        const f = familyById('wan2.2');  // fixed 5s
        expect(clampDuration(f, 1)).toBe(5);
        expect(clampDuration(f, 5)).toBe(5);
        expect(clampDuration(f, 99)).toBe(5);
    });

    it('slider: 越界回落到 default，否则保留', () => {
        const f = familyById('wan2.6');  // 2..15
        expect(clampDuration(f, 7)).toBe(7);
        expect(clampDuration(f, 1)).toBe(5);   // < min → default
        expect(clampDuration(f, 99)).toBe(5);  // > max → default
    });

    it('buttons: 不在 options 中回落到 default', () => {
        const f = familyById('wan2.5');  // [5, 10]
        expect(clampDuration(f, 5)).toBe(5);
        expect(clampDuration(f, 10)).toBe(10);
        expect(clampDuration(f, 7)).toBe(5);   // not an option → default
    });
});

// ── familyDefaults — reset values when picker switches family ────────────

describe('familyDefaults', () => {
    it('Wan 2.6: promptExtend=true, resolution=720p', () => {
        const d = familyDefaults(familyById('wan2.6'));
        expect(d.promptExtend).toBe(true);
        expect(d.resolution).toBe('720p');
        expect(d.duration).toBe(5);
    });

    it('Kling: cfgScale=0.5, mode=std, promptExtend=false', () => {
        const d = familyDefaults(familyById('kling'));
        expect(d.cfgScale).toBe(0.5);
        expect(d.mode).toBe('std');
        expect(d.promptExtend).toBe(false);
    });

    it('Vidu: movementAmplitude=auto, viduAudio=true', () => {
        const d = familyDefaults(familyById('vidu'));
        expect(d.movementAmplitude).toBe('auto');
        expect(d.viduAudio).toBe(true);
    });

    it('Wan 2.2: fixed duration 强制为 5', () => {
        const d = familyDefaults(familyById('wan2.2'));
        expect(d.duration).toBe(5);
    });
});

// ── GRID_COLS_CLASS coverage ─────────────────────────────────────────────

describe('GRID_COLS_CLASS', () => {
    it('返回稳定的 grid-cols-N tokens', () => {
        expect(GRID_COLS_CLASS[2]).toBe('grid-cols-2');
        expect(GRID_COLS_CLASS[3]).toBe('grid-cols-3');
        expect(GRID_COLS_CLASS[4]).toBe('grid-cols-4');
    });

    it('覆盖所有 family 实际使用的列数', () => {
        const used = new Set<number>();
        for (const f of I2V_FAMILIES) {
            const p = f.params;
            if (p.resolution) used.add(p.resolution.options.length);
            if (p.mode) used.add(p.mode.options.length);
            if (p.movementAmplitude) used.add(p.movementAmplitude.options.length);
            if (f.duration.type === 'buttons') used.add(f.duration.options.length);
        }
        used.forEach((n) => expect(GRID_COLS_CLASS[n]).toBeDefined());
    });
});
