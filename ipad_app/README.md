# iPad App - Welding Session Recorder

React Native app built with Expo for recording and managing welding sessions.

## Setup

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm start
```

## Testing

### Running Tests

```bash
npm test
```

### Testing on Expo Go

1. Install Expo Go on your iPad from the App Store
2. Start the development server: `npm start`
3. Scan the QR code with your iPad camera
4. The app will open in Expo Go

### Testing on iOS Simulator

1. Install Xcode and iOS Simulator
2. Start the development server: `npm start`
3. Press `i` to open in iOS Simulator

## Components

- **App.tsx** - Main app entry point
- **SensorSync.tsx** - Checks all sensors are connected
- **SessionRecorder.tsx** - Buffers and sends session JSON
- **Dashboard.tsx** - Replay + metrics visualization

## API Client

The `api/backendClient.ts` module handles all REST calls to the FastAPI backend.

## Development Status

⚠️ **Placeholder Implementation** - Components are currently placeholders. Full implementation will be added later.
