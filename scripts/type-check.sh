#!/bin/bash
# Type checking script for frontend
# Runs TypeScript compiler to check for type errors

set -e

echo "🔍 Running TypeScript type check..."

cd my-app
npx tsc --noEmit

echo "✅ Type check passed!"
