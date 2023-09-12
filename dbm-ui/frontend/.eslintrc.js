/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
*/

module.exports = {
  root: true,
  extends: [
    'eslint-config-tencent',
    'plugin:vue/vue3-recommended',
    'eslint:recommended',
    '@vue/eslint-config-typescript/recommended',
    './.eslintrc-auto-import.json',
  ],
  plugins: [
    'simple-import-sort',
  ],
  env: {
    es6: true,
    node: true,
    jest: true,
    browser: true,
    'vue/setup-compiler-macros': true,
  },
  globals: {
    defineModel: 'readonly',
    // value 为 true 允许被重写，为 false 不允许被重写
    __RESOURCE_UNIQUE_KEY__: false,
    ValueOf: false,
  },
  rules: {
    '@typescript-eslint/no-explicit-any': 'off',
    // 对象写在一行时，大括号里需要空格
    // 'object-curly-spacing': ['error', 'always'],
    'simple-import-sort/exports': 'error',
    'simple-import-sort/imports': ['error', {
      groups: [
        ['^[a-zA-Z]'],
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
        ['^@locales'],
        ['^@images'],
        ['^@\\w'],
        ['^\\.\\.'],
        ['^\\.'],
      ],
    }],
    'vue/multi-word-component-names': 'off',
  },
  overrides: [
    {
      files: ['*.vue'],
      rules: {
        indent: 'off',
        'import/first': 'off',
        'vue/html-closing-bracket-newline': ['error', {
          singleline: 'never',
          multiline: 'never',
        }],
        'vue/component-tags-order': ['warn', {
          order: ['template', 'script', 'style'],
        }],
        'vue/attributes-order': ['error', {
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
        }],
        'vue/define-macros-order': ['error', {
          order: ['defineProps', 'defineEmits'],
        }],
        'vue/no-undef-properties': ['error', {
          ignores: ['/^\\$/'],
        }],
        'vue/no-unused-properties': ['error', {
          groups: ['props'],
          deepData: false,
          ignorePublicMembers: false,
        }],
        'vue/no-useless-mustaches': ['error', {
          ignoreIncludesComment: false,
          ignoreStringEscape: false,
        }],
        'vue/no-useless-v-bind': ['error', {
          ignoreIncludesComment: false,
          ignoreStringEscape: false,
        }],
        'vue/prefer-separate-static-class': 'error',
        'vue/prefer-true-attribute-shorthand': 'error',
        'vue/script-indent': ['error', 2, {
          baseIndent: 1,
        }],
        'vue/component-name-in-template-casing': ['error', 'PascalCase', {
          registeredComponentsOnly: false,
          ignores: [],
        }],
      },
    },
  ],
};
