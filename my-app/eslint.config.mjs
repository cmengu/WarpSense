import { createRequire } from "node:module";
import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const require = createRequire(import.meta.url);
const maxTorchviz3dRule = require("./eslint-rules/max-torchviz3d-per-page.cjs");
const maxTorchvizPlugin = {
  rules: { "max-torchviz3d-per-page": maxTorchviz3dRule },
};

// WebGL context limit: max 2 TorchViz3D per page — see src/constants/webgl.ts
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  // Max TorchViz3D per page: applies to app page files, excludes __tests__ and dev/
  {
    files: ["src/app/**/page.tsx"],
    ignores: ["**/__tests__/**", "**/dev/**"],
    plugins: { "max-torchviz": maxTorchvizPlugin },
    rules: { "max-torchviz/max-torchviz3d-per-page": ["error", 2] },
  },
]);

export default eslintConfig;
