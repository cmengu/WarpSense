#!/usr/bin/env bash
# Fix framer-motion module-not-found: installs missing deps per .cursor/plans/fix-framer-motion-module-not-found-plan.md
set -e
cd "$(dirname "$0")/../my-app"
echo "Installing dependencies (including framer-motion) with --legacy-peer-deps..."
npm install --legacy-peer-deps
echo "Verifying build..."
npm run build
echo "Done. framer-motion should now resolve."
