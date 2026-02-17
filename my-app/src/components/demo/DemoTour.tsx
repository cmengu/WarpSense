'use client';

/**
 * DemoTour — Custom overlay for guided demo narrative.
 *
 * Config-driven steps, focus trap, a11y (aria-modal, role="dialog"),
 * Escape to skip. z-[200] + isolate to appear above 3D Canvas.
 * Contingency: z-[300] if Safari has stacking issues.
 */

import { useState, useCallback, useEffect, useRef } from 'react';
import type { TourStep } from '@/lib/demo-tour-config';

interface DemoTourProps {
  steps: TourStep[];
  onStepEnter?: (step: TourStep) => void;
  onComplete?: () => void;
  onSkip?: () => void;
  onStepLog?: (step: TourStep, index: number) => void;
}

const FOCUSABLE_SELECTOR =
  'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])';

export function DemoTour({
  steps,
  onStepEnter,
  onComplete,
  onSkip,
  onStepLog,
}: DemoTourProps) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isDismissed, setIsDismissed] = useState(false);
  const overlayRef = useRef<HTMLDivElement>(null);

  const step = steps[currentIndex];

  useEffect(() => {
    if (!overlayRef.current || !step) return;
    const el = overlayRef.current;
    const focusables = el.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR);
    if (focusables.length > 0 && !el.contains(document.activeElement)) {
      (focusables[0] as HTMLElement).focus();
    }
  }, [currentIndex, step]);

  useEffect(() => {
    if (step) {
      onStepEnter?.(step);
      onStepLog?.(step, currentIndex);
    }
  }, [step, onStepEnter, onStepLog, currentIndex]);

  const handleNext = useCallback(() => {
    const s = steps[currentIndex];
    if (s?.isLast) {
      onComplete?.();
      setIsDismissed(true);
      return;
    }
    setCurrentIndex((i) => Math.min(i + 1, steps.length - 1));
  }, [currentIndex, steps, onComplete]);

  const handleSkip = useCallback(() => {
    onSkip?.();
    setIsDismissed(true);
  }, [onSkip]);

  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        handleSkip();
      }
    };
    document.addEventListener('keydown', h);
    return () => document.removeEventListener('keydown', h);
  }, [handleSkip]);

  if (isDismissed || steps.length === 0) return null;
  if (!step) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-[200] isolate flex items-center justify-center p-4 transition-all duration-200"
      role="dialog"
      aria-modal="true"
      aria-labelledby="tour-title"
      aria-describedby="tour-body"
    >
      <div
        className="absolute inset-0 bg-black/60"
        onClick={handleSkip}
        role="button"
        tabIndex={0}
        aria-label="Click to skip tour"
        onKeyDown={(e) => e.key === 'Enter' && handleSkip()}
      />
      <div className="relative z-10 bg-neutral-900 border-2 border-blue-400 rounded-lg p-6 max-w-md w-full shadow-xl min-w-[280px] max-w-[calc(100vw-2rem)]">
        <h2 id="tour-title" className="text-xl font-bold text-blue-400 mb-2">
          {step.title}
        </h2>
        <p id="tour-body" className="text-gray-300 mb-6">
          {step.body}
        </p>
        <div className="flex justify-between gap-4">
          <button
            type="button"
            onClick={handleSkip}
            className="px-4 py-2 text-gray-400 hover:text-white transition"
            aria-label="Skip tour"
          >
            Skip tour
          </button>
          <button
            type="button"
            onClick={handleNext}
            className="px-6 py-2 bg-blue-400 text-black font-bold rounded hover:bg-blue-300 transition"
            aria-label={step.nextLabel}
          >
            {step.nextLabel}
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-4">
          Step {currentIndex + 1} of {steps.length}
        </p>
      </div>
    </div>
  );
}
