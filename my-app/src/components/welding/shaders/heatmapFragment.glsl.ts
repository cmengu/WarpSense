/**
 * Fragment shader for 3D heatmap plate.
 *
 * Maps vTemperature to color via stepped gradient (5–10°C visible steps).
 * 8 anchor colors, green (cold) → orange → red (hot). IR-style thermal.
 *
 * @see my-app/src/constants/theme.ts (THERMAL_ANCHOR_COLORS_0_1)
 */

export const heatmapFragmentShader = `
varying vec2 vUv;
varying float vTemperature;
uniform float uMinTemp;
uniform float uMaxTemp;
uniform float uStepCelsius;

vec3 temperatureToColor(float temp) {
  float range = max(1.0, uMaxTemp - uMinTemp);
  float t = clamp((temp - uMinTemp) / range, 0.0, 1.0);
  if (t != t) t = 0.0;
  float numSteps = max(1.0, range / uStepCelsius);
  float stepIndex = clamp(floor(t * numSteps), 0.0, numSteps - 1.0);
  float stepNorm = stepIndex / numSteps;

  float anchorPos[8];
  anchorPos[0] = 0.0;  anchorPos[1] = 0.1;  anchorPos[2] = 0.2;  anchorPos[3] = 0.3;
  anchorPos[4] = 0.5;  anchorPos[5] = 0.7;  anchorPos[6] = 0.9;  anchorPos[7] = 1.0;

  vec3 anchorCol[8];
  anchorCol[0] = vec3(0.55, 0.55, 0.55);  // cool gray (ambient)
  anchorCol[1] = vec3(0.18, 0.72, 0.38);  // green (cold weld)
  anchorCol[2] = vec3(0.40, 0.78, 0.22);  // yellow-green
  anchorCol[3] = vec3(0.85, 0.75, 0.10);  // yellow
  anchorCol[4] = vec3(0.95, 0.55, 0.05);  // orange
  anchorCol[5] = vec3(0.95, 0.30, 0.05);  // orange-red
  anchorCol[6] = vec3(0.85, 0.10, 0.05);  // red
  anchorCol[7] = vec3(0.98, 0.05, 0.05);  // hot red

  int seg = 0;
  for (int i = 0; i < 7; i++) {
    if (stepNorm >= anchorPos[i]) seg = i;
  }
  float low = anchorPos[seg];
  float high = anchorPos[seg + 1];
  float denom = high - low;
  float mixF = (denom < 0.001) ? 1.0 : clamp((stepNorm - low) / denom, 0.0, 1.0);
  return mix(anchorCol[seg], anchorCol[seg + 1], mixF);
}

void main() {
  vec3 color = temperatureToColor(vTemperature);
  gl_FragColor = vec4(color, 1.0);
}
`;
