/**
 * SensorSync Component Test
 * Tests that the SensorSync placeholder component renders
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import SensorSync from '../components/SensorSync';

describe('SensorSync', () => {
  it('renders placeholder content', () => {
    const { getByText } = render(<SensorSync />);
    expect(getByText(/SensorSync Component/i)).toBeTruthy();
    expect(getByText(/Coming soon/i)).toBeTruthy();
  });
});
