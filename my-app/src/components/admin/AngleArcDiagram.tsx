'use client';

interface AngleArcDiagramProps {
  angleTargetDegrees: number;
  className?: string;
}

/**
 * Inline SVG semicircle showing target angle as an arc.
 * Arc spans 0° to angleTargetDegrees (validation limits to ≤90°).
 */
export default function AngleArcDiagram({
  angleTargetDegrees,
  className = '',
}: AngleArcDiagramProps) {
  const r = 24;
  const cx = 30;
  const cy = 30;
  const startAngle = 0;
  const endAngle = (angleTargetDegrees / 180) * Math.PI;
  const x1 = cx + r * Math.cos(startAngle);
  const y1 = cy - r * Math.sin(startAngle);
  const x2 = cx + r * Math.cos(endAngle);
  const y2 = cy - r * Math.sin(endAngle);
  const d = `M ${cx} ${cy} L ${x1} ${y1} A ${r} ${r} 0 0 1 ${x2} ${y2} Z`;
  return (
    <svg
      width="60"
      height="40"
      viewBox="0 0 60 40"
      className={className}
      role="img"
      aria-label={`Target angle: ${angleTargetDegrees} degrees`}
    >
      <path d={d} fill="none" stroke="currentColor" strokeWidth="2" />
      <text x="30" y="38" textAnchor="middle" fontSize="10">
        {angleTargetDegrees}°
      </text>
    </svg>
  );
}
