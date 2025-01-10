import tencentConfig from 'eslint-config-tencent/ts';
import importPlugin from 'eslint-plugin-import';
import oxlint from 'eslint-plugin-oxlint';
// import perfectionist from 'eslint-plugin-perfectionist';
import simpleImportSortPlugin from 'eslint-plugin-simple-import-sort';
import pluginVue from 'eslint-plugin-vue';
import globals from 'globals';

import skipFormatting from '@vue/eslint-config-prettier/skip-formatting';
import { configureVueProject, defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript';

const tencentRule = tencentConfig.rules;

// eslint-config-tencent/ts 依赖的 @typescript-eslint 版本过低，部分规则配置已经废弃需要删除
delete tencentRule['@typescript-eslint/quotes'];
delete tencentRule['@typescript-eslint/brace-style'];
delete tencentRule['@typescript-eslint/comma-spacing'];
delete tencentRule['@typescript-eslint/func-call-spacing'];
delete tencentRule['@typescript-eslint/indent'];
delete tencentRule['@typescript-eslint/keyword-spacing'];
delete tencentRule['@typescript-eslint/semi'];
delete tencentRule['@typescript-eslint/type-annotation-spacing'];
delete tencentRule['@typescript-eslint/space-before-function-paren'];

configureVueProject({
  scriptLangs: ['ts', 'tsx'],
});

export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  {
    name: 'app/files-to-ignore',
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**'],
  },
  pluginVue.configs['flat/recommended'],
  vueTsConfigs.recommended,
  oxlint.configs['flat/recommended'],
  skipFormatting,
  {
    languageOptions: {
      ecmaVersion: 5,
      sourceType: 'script',
      parserOptions: {
        ecmaFeatures: {
          jsx: true,
        },
      },
      globals: {
        ...globals.browser,
        defineModel: 'readonly',
        ValueOf: 'readonly',
        ServiceReturnType: 'readonly',
        ServiceParameters: 'readonly',
        SelectItem: 'readonly',
        KeyExpand: 'readonly',
      },
    },
  },
  {
    files: ['**/*.ts', '**/*.tsx', '**/*.vue'],
    rules: {
      ...tencentRule,
      '@typescript-eslint/no-explicit-any': 'off',
      '@typescript-eslint/consistent-type-assertions': 'off',
      '@typescript-eslint/naming-convention': [
        'error',
        {
          selector: 'variable',
          format: ['camelCase', 'UPPER_CASE'],
        },
      ],
      'no-underscore-dangle': ['error', { enforceInMethodNames: false }],
      'no-param-reassign': ['error', { props: true }],
    },
  },
  // {
  //   files: ['**/*.ts', '**/*.tsx', '**/*.vue'],
  //   plugins: {
  //     perfectionist,
  //   },
  //   rules: {
  //     'perfectionist/sort-jsx-props': [
  //       'error',
  //       {
  //         type: 'alphabetical',
  //         order: 'asc',
  //         ignoreCase: true,
  //         specialCharacters: 'keep',
  //         ignorePattern: [],
  //         partitionByNewLine: false,
  //         newlinesBetween: 'ignore',
  //         groups: [
  //           'DEFINITION',
  //           'LIST_RENDERING',
  //           'CONDITIONALS',
  //           'RENDER_MODIFIERS',
  //           'GLOBAL',
  //           'UNIQUE',
  //           'SLOT',
  //           'TWO_WAY_BINDING',
  //           'OTHER_DIRECTIVES',
  //           'multiline',
  //           'unknown',
  //           'shorthand',
  //           'callback',
  //         ],
  //         customGroups: {
  //           DEFINITION: '^v-is',
  //           LIST_RENDERING: '^v-for',
  //           CONDITIONALS: '^(v-if|v-else-if|v-else|v-show|v-cloak)',
  //           RENDER_MODIFIERS: '^(v-once|v-pre)',
  //           GLOBAL: '^id',
  //           UNIQUE: '^(ref|key)',
  //           SLOT: '^v-slot',
  //           TWO_WAY_BINDING: '^v-model',
  //           OTHER_DIRECTIVES: '^v-.+',
  //           callback: '^on.+',
  //         },
  //       },
  //     ],
  //     'perfectionist/sort-array-includes': 'error',
  //     'perfectionist/sort-classes': [
  //       'error',
  //       {
  //         type: 'alphabetical',
  //         order: 'asc',
  //         ignoreCase: true,
  //         specialCharacters: 'keep',
  //         partitionByComment: false,
  //         partitionByNewLine: false,
  //         newlinesBetween: 'ignore',
  //         ignoreCallbackDependenciesPatterns: [],
  //         groups: [
  //           'index-signature',
  //           ['static-property', 'static-accessor-property'],
  //           ['static-get-method', 'static-set-method'],
  //           ['protected-static-property', 'protected-static-accessor-property'],
  //           ['protected-static-get-method', 'protected-static-set-method'],
  //           ['private-static-property', 'private-static-accessor-property'],
  //           ['private-static-get-method', 'private-static-set-method'],
  //           'static-block',
  //           ['static-method', 'static-function-property'],
  //           ['protected-static-method', 'protected-static-function-property'],
  //           ['private-static-method', 'private-static-function-property'],
  //           ['property', 'accessor-property'],
  //           ['protected-property', 'protected-accessor-property'],
  //           ['protected-get-method', 'protected-set-method'],
  //           ['private-property', 'private-accessor-property'],
  //           ['private-get-method', 'private-set-method'],
  //           'constructor',
  //           ['get-method', 'set-method'],
  //           ['method', 'function-property'],
  //           ['protected-method', 'protected-function-property'],
  //           ['private-method', 'private-function-property'],
  //           'unknown',
  //         ],
  //         customGroups: [],
  //       },
  //     ],
  //     'perfectionist/sort-enums': 'error',
  //     'perfectionist/sort-intersection-types': 'error',
  //     'perfectionist/sort-interfaces': 'error',
  //     'perfectionist/sort-named-imports': 'error',
  //     'perfectionist/sort-object-types': 'error',
  //     'perfectionist/sort-objects': 'error',
  //   },
  // },
  {
    plugins: {
      import: importPlugin,
    },
    rules: {
      'import/first': 'off',
      'import/newline-after-import': 'error',
      'import/no-duplicates': 'error',
    },
  },
  {
    plugins: {
      'simple-import-sort': simpleImportSortPlugin,
    },
    rules: {
      'simple-import-sort/exports': 'error',
      'simple-import-sort/imports': [
        'error',
        {
          groups: [
            ['^[a-zA-Z]'], // 普通 npm 包
            ['^@blueking'],
            ['^@services'],
            ['^@hooks'],
            ['^@router'],
            ['^@stores'],
            ['^@common'],
            ['^@components'],
            ['^@views'],
            ['^@utils'],
            ['^@helper'],
            ['^@types'],
            ['^@locales'],
            ['^@styles'],
            ['^@images'],
            ['^[^.]'],
            ['^\\.\\.'], // 父目录相对路径
            ['^\\.'], // 当前目录相对路径
          ],
        },
      ],
    },
  },
  {
    files: ['**/*.vue'],
    rules: {
      indent: 'off',
      'vue/multi-word-component-names': 'off',
      'vue/html-closing-bracket-newline': [
        'error',
        {
          singleline: 'never',
          multiline: 'never',
        },
      ],
      'vue/component-tags-order': ['warn', { order: ['template', 'script', 'style'] }],
      'vue/attributes-order': [
        'error',
        {
          order: [
            'DEFINITION',
            'LIST_RENDERING',
            'CONDITIONALS',
            'RENDER_MODIFIERS',
            'GLOBAL',
            ['UNIQUE', 'SLOT'],
            'TWO_WAY_BINDING',
            'OTHER_DIRECTIVES',
            'OTHER_ATTR',
            'EVENTS',
            'CONTENT',
          ],
          alphabetical: true,
        },
      ],
      'vue/define-macros-order': ['error', { order: ['defineProps', 'defineEmits'] }],
      'vue/no-undef-properties': ['error', { ignores: ['/^\\$/'] }],
      'vue/no-unused-properties': [
        'error',
        {
          groups: ['props'],
          deepData: false,
          ignorePublicMembers: false,
        },
      ],
      'vue/no-useless-mustaches': [
        'error',
        {
          ignoreIncludesComment: false,
          ignoreStringEscape: false,
        },
      ],
      'vue/no-useless-v-bind': [
        'error',
        {
          ignoreIncludesComment: false,
          ignoreStringEscape: false,
        },
      ],
      'vue/prefer-separate-static-class': 'error',
      'vue/prefer-true-attribute-shorthand': 'error',
      'vue/script-indent': ['off', 2, { baseIndent: 1 }],
      'vue/component-name-in-template-casing': [
        'error',
        'PascalCase',
        {
          registeredComponentsOnly: false,
          ignores: [],
        },
      ],
      'vue/no-setup-props-reactivity-loss': 'off',
      'vue/no-setup-props-destructure': 'off',
    },
  },
  {
    ignores: [
      'node_modules/*',
      'dist/*',
      'public/*',
      'src/types/auto-imports.d.ts',
      'patch/*',
      'lib/*',
      'auto-copyright.js',
    ],
  },
);
