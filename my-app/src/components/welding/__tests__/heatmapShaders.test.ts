/**
 * ShaderSmokeTest — Step 1.3b.
 *
 * Verifies heatmap vertex and fragment shaders can be used to construct a
 * Three.js ShaderMaterial without throwing. Catches obvious shader string
 * issues before full Plate integration. Actual WebGL compile happens at
 * render time; this validates structure and uniform setup.
 *
 * @see .cursor/plans/3d-warped-heatmap-plate-implementation-plan.md Step 1.3b
 */

import * as THREE from 'three';
import { heatmapVertexShader } from '../shaders/heatmapVertex.glsl';
import { heatmapFragmentShader } from '../shaders/heatmapFragment.glsl';

describe('Heatmap shaders (ShaderSmokeTest)', () => {
  it('ShaderMaterial constructs without throw with heatmap shaders', () => {
    const data = new Float32Array(100 * 100);
    data.fill(100); // 100°C default
    const texture = new THREE.DataTexture(
      data,
      100,
      100,
      THREE.RedFormat,
      THREE.FloatType
    );
    texture.needsUpdate = true;

    expect(() => {
      new THREE.ShaderMaterial({
        vertexShader: heatmapVertexShader,
        fragmentShader: heatmapFragmentShader,
        uniforms: {
          uTemperatureMap: { value: texture },
          uMaxTemp: { value: 600 },
          uMaxDisplacement: { value: 0.5 },
        },
        side: THREE.DoubleSide,
      });
    }).not.toThrow();
  });

  it('shader strings are non-empty', () => {
    expect(heatmapVertexShader).toBeDefined();
    expect(heatmapVertexShader.length).toBeGreaterThan(0);
    expect(heatmapFragmentShader).toBeDefined();
    expect(heatmapFragmentShader.length).toBeGreaterThan(0);
  });

  it('vertex shader declares vUv and vTemperature', () => {
    expect(heatmapVertexShader).toContain('varying vec2 vUv');
    expect(heatmapVertexShader).toContain('varying float vTemperature');
  });

  it('fragment shader declares matching varyings', () => {
    expect(heatmapFragmentShader).toContain('varying vec2 vUv');
    expect(heatmapFragmentShader).toContain('varying float vTemperature');
  });
});
