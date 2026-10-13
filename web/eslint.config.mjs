import typescriptEslint from "typescript-eslint";

const config = typescriptEslint.config(
	{ ignores: [".next/**", "node_modules/**", "next-env.d.ts"] },
	...typescriptEslint.configs.recommended,
);

export default config;