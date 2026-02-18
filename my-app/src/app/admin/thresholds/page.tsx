'use client';

import { useState, useEffect } from 'react';
import {
  fetchThresholds,
  updateThreshold,
} from '@/lib/api';
import type { WeldTypeThresholds } from '@/types/thresholds';
import AngleArcDiagram from '@/components/admin/AngleArcDiagram';

const TABS = ['mig', 'tig', 'stick', 'flux_core'] as const;

function isCompleteForm(
  f: Partial<WeldTypeThresholds>
): f is WeldTypeThresholds {
  const isNum = (v: unknown) =>
    typeof v === 'number' && Number.isFinite(v) && v >= 0;
  return (
    isNum(f.angle_target_degrees) &&
    (f.angle_target_degrees ?? 0) > 0 &&
    isNum(f.angle_warning_margin) &&
    isNum(f.angle_critical_margin) &&
    isNum(f.thermal_symmetry_warning_celsius) &&
    isNum(f.thermal_symmetry_critical_celsius) &&
    isNum(f.amps_stability_warning) &&
    isNum(f.volts_stability_warning) &&
    isNum(f.heat_diss_consistency)
  );
}

export default function AdminThresholdsPage() {
  const [all, setAll] = useState<WeldTypeThresholds[]>([]);
  const [fetchError, setFetchError] = useState<string | null>(null);
  const [active, setActive] = useState<(typeof TABS)[number]>('mig');
  const [form, setForm] = useState<Partial<WeldTypeThresholds>>({});
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchThresholds()
      .then(setAll)
      .catch((e) => setFetchError(String(e)));
  }, []);

  const current = all.find((t) => t.weld_type === active);
  useEffect(() => {
    if (current) setForm({ ...current });
  }, [active, current]);

  const canSave =
    !fetchError &&
    all.length > 0 &&
    isCompleteForm(form) &&
    !saving &&
    (form.angle_target_degrees ?? 0) > 0;

  const handleSave = async () => {
    if (!canSave || !isCompleteForm(form)) return;
    if ((form.angle_target_degrees ?? 0) <= 0) {
      setError('angle_target_degrees must be > 0');
      return;
    }
    if (
      (form.angle_warning_margin ?? 0) > (form.angle_critical_margin ?? 0)
    ) {
      setError('angle_warning_margin must be <= angle_critical_margin');
      return;
    }
    if (
      (form.thermal_symmetry_warning_celsius ?? 0) >
      (form.thermal_symmetry_critical_celsius ?? 0)
    ) {
      setError(
        'thermal_symmetry_warning must be <= thermal_symmetry_critical'
      );
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await updateThreshold(active, form);
      const updated = await fetchThresholds();
      setAll(updated);
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const num = (v: number | undefined): number =>
    typeof v === 'number' && Number.isFinite(v) ? v : 0;
  const parsed = (s: string): number | undefined => {
    const n = parseFloat(s);
    return Number.isFinite(n) ? n : undefined;
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4 text-zinc-900 dark:text-zinc-50">
        Weld Quality Thresholds
      </h1>
      {fetchError && (
        <p className="text-red-600 dark:text-red-400 mb-4">
          Failed to load thresholds: {fetchError}
        </p>
      )}
      <div role="tablist" className="flex gap-2 mb-6">
        {TABS.map((t) => (
          <button
            key={t}
            type="button"
            role="tab"
            aria-selected={active === t}
            onClick={() => setActive(t)}
            className={`px-4 py-2 rounded-md font-medium ${
              active === t
                ? 'bg-blue-600 text-white'
                : 'bg-zinc-200 dark:bg-zinc-700 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-300 dark:hover:bg-zinc-600'
            }`}
          >
            {t.toUpperCase()}
          </button>
        ))}
      </div>
      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3 text-zinc-800 dark:text-zinc-200">
          Angle
        </h2>
        <div className="flex flex-wrap items-center gap-4">
          <label className="flex items-center gap-2">
            Target
            <input
              type="number"
              min={0.1}
              max={90}
              step={1}
              value={form.angle_target_degrees ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  angle_target_degrees: parsed(e.target.value),
                }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
            °
          </label>
          <AngleArcDiagram
            angleTargetDegrees={
              Number.isFinite(form.angle_target_degrees)
                ? (form.angle_target_degrees ?? 45)
                : 45
            }
          />
          <label className="flex items-center gap-2">
            Warning ±
            <input
              type="number"
              min={0}
              max={45}
              step={1}
              value={form.angle_warning_margin ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  angle_warning_margin: parsed(e.target.value),
                }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
            °
          </label>
          <label className="flex items-center gap-2">
            Critical ±
            <input
              type="number"
              min={0}
              max={45}
              step={1}
              value={form.angle_critical_margin ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  angle_critical_margin: parsed(e.target.value),
                }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
            °
          </label>
        </div>
      </section>
      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3 text-zinc-800 dark:text-zinc-200">
          Thermal / Amps / Volts / Heat Diss
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <label className="flex items-center gap-2">
            Thermal warning °C
            <input
              type="number"
              min={0}
              max={200}
              step={1}
              value={form.thermal_symmetry_warning_celsius ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  thermal_symmetry_warning_celsius: parsed(e.target.value),
                }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
          </label>
          <label className="flex items-center gap-2">
            Thermal critical °C
            <input
              type="number"
              min={0}
              max={200}
              step={1}
              value={form.thermal_symmetry_critical_celsius ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  thermal_symmetry_critical_celsius: parsed(e.target.value),
                }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
          </label>
          <label className="flex items-center gap-2">
            Amps stability
            <input
              type="number"
              min={0}
              step={0.1}
              value={form.amps_stability_warning ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  amps_stability_warning: parsed(e.target.value),
                }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
          </label>
          <label className="flex items-center gap-2">
            Volts stability
            <input
              type="number"
              min={0}
              step={0.1}
              value={form.volts_stability_warning ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  volts_stability_warning: parsed(e.target.value),
                }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
          </label>
          <label className="flex items-center gap-2">
            Heat diss consistency
            <input
              type="number"
              min={0}
              step={0.1}
              value={form.heat_diss_consistency ?? ''}
              onChange={(e) =>
                setForm((f) => ({
                  ...f,
                  heat_diss_consistency: parsed(e.target.value),
                }))
              }
              className="w-20 px-2 py-1 border rounded"
            />
          </label>
        </div>
      </section>
      <button
        type="button"
        onClick={handleSave}
        disabled={!canSave}
        aria-busy={saving}
        className="px-4 py-2 rounded-md bg-blue-600 text-white font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {saving ? 'Saving…' : 'Save Changes'}
      </button>
      {error && (
        <p
          className="text-red-600 dark:text-red-400 mt-2"
          data-testid="validation-error"
        >
          {error}
        </p>
      )}
    </div>
  );
}
