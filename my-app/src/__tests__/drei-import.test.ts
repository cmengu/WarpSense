/**
 * Step 1 verification: Confirm @react-three/drei imports correctly.
 * This test validates that OrbitControls (and other drei exports) can be imported
 * without TypeScript or module resolution errors.
 */
import { OrbitControls, Environment, ContactShadows } from '@react-three/drei';

describe('@react-three/drei import', () => {
  it('imports OrbitControls', () => {
    expect(OrbitControls).toBeDefined();
    expect(typeof OrbitControls).toMatch(/function|object/); // React forwardRef components
  });

  it('imports Environment', () => {
    expect(Environment).toBeDefined();
    expect(typeof Environment).toMatch(/function|object/);
  });

  it('imports ContactShadows', () => {
    expect(ContactShadows).toBeDefined();
    expect(typeof ContactShadows).toMatch(/function|object/);
  });
});
