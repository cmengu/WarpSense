/**
 * Vertex shader for 3D heatmap plate.
 *
 * Samples temperature from uTemperatureMap texture, displaces vertices along
 * normal to simulate thermal expansion. Uses WebGL 1 texture2D().
 *
 * @see .cursor/plans/3d-warped-heatmap-plate-implementation-plan.md Step 1.3
 */

export const heatmapVertexShader = `
varying vec2 vUv;
varying float vTemperature;
uniform sampler2D uTemperatureMap;
uniform float uMaxDisplacement;
uniform float uMaxTemp;

void main() {
  vUv = uv;
  float temperature = texture2D(uTemperatureMap, uv).r;
  vTemperature = temperature;
  float safeMaxTemp = max(uMaxTemp, 0.001);
  float displacement = (temperature / safeMaxTemp) * uMaxDisplacement;
  vec3 newPosition = position + normal * displacement;
  gl_Position = projectionMatrix * modelViewMatrix * vec4(newPosition, 1.0);
}
`;
