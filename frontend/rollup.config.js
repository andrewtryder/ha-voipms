import { nodeResolve } from "@rollup/plugin-node-resolve";
import typescript from "@rollup/plugin-typescript";

export default {
  input: "src/voipms-sms-card.ts",
  output: {
    file: "../custom_components/voipms/frontend/voipms-sms-card.js",
    format: "es",
    sourcemap: false,
  },
  plugins: [
    nodeResolve(),
    typescript({
      tsconfig: "./tsconfig.json",
      declaration: false,
      sourceMap: false,
    }),
  ],
};
