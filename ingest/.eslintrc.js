module.exports = {
  env: {
    browser: true,
    commonjs: true,
    es6: true,
    node: true
  },
  extends: [
    'standard'
  ],
  globals: {
    Atomics: 'readonly',
    SharedArrayBuffer: 'readonly'
  },
  parserOptions: {
    ecmaVersion: 2018
  },
  rules: {
    "comma-dangle": ["error", "always-multiline"],
    "semi": ["error", "always"],
    "space-before-function-paren": ["error", "never"],
    "no-var": ["error"],
    "prefer-const": ["error"],
  }
}
