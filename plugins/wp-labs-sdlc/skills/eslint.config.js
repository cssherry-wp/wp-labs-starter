import html from "eslint-plugin-html";
import globals from "globals";

export default [
  {
    files: ["**/*.html"],
    plugins: { html },
    languageOptions: {
      globals: {
        ...globals.browser,
        // File System Access API (not yet in globals.browser)
        showDirectoryPicker: "readonly",
        showOpenFilePicker: "readonly",
        FileSystemDirectoryHandle: "readonly",
        FileSystemFileHandle: "readonly",
      },
    },
    rules: {
      // Correctness only — no formatting rules
      "no-unreachable": "error",
      "no-dupe-keys": "error",
      "no-duplicate-case": "error",
      "use-isnan": "error",
      "eqeqeq": ["warn", "smart"],
      "no-undef": "warn",
      // vars:local skips top-level functions/globals intentionally exported via window
      "no-unused-vars": ["warn", { "vars": "local", "args": "none" }],
    },
  },
];
