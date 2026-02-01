/**
 * App Component Test
 * Tests that the main App component renders correctly
 */

import React from 'react';
import { render } from '@testing-library/react-native';
import App from '../App';

describe('App', () => {
  it('renders correctly', () => {
    const { getByText } = render(<App />);
    expect(getByText('Welding Session Recorder')).toBeTruthy();
    expect(getByText('Coming soon')).toBeTruthy();
  });
});
