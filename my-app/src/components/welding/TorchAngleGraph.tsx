'use client';

/**
 * TorchAngleGraph Component
 * Graphs torch angle over time for a welding session
 * 
 * @param sessionId - Session ID to display torch angle graph for
 */

interface TorchAngleGraphProps {
  sessionId: string;
}

export default function TorchAngleGraph({ sessionId }: TorchAngleGraphProps) {
  return (
    <div className="torch-angle-graph-container bg-white dark:bg-zinc-900 rounded-lg border border-zinc-200 dark:border-zinc-800 p-6">
      <h3 className="text-lg font-semibold mb-4 text-black dark:text-zinc-50">
        Torch Angle Over Time
      </h3>
      <div className="placeholder-visualization text-zinc-500 dark:text-zinc-400 min-h-[300px] flex items-center justify-center border border-dashed border-zinc-300 dark:border-zinc-700 rounded">
        <div className="text-center">
          <p className="text-sm">Torch angle graph for session {sessionId}</p>
          <p className="text-xs mt-2">Coming soon</p>
        </div>
      </div>
    </div>
  );
}
