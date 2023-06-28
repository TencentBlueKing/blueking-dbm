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

import { resolve } from 'path';
import AutoImport from 'unplugin-auto-import/vite';
import { defineConfig, loadEnv } from 'vite';
import  ViteHTMLEnv from 'vite-plugin-html-env';
import monacoEditorPlugin from 'vite-plugin-monaco-editor';
import { viteStaticCopy } from 'vite-plugin-static-copy';

import basicSsl from '@vitejs/plugin-basic-ssl';
import vue from '@vitejs/plugin-vue';
import vueJsx from '@vitejs/plugin-vue-jsx';

// 用于判断前端资源更新
const uniqueKey = `${new Date().getTime()}.1e78f18e-01c1-11ed-b939-0242ac120002`;

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  const isHttps = process.argv.includes('--https');

  return {
    base: env.VITE_PUBLIC_PATH,
    define: {
      __RESOURCE_UNIQUE_KEY__: JSON.stringify(uniqueKey),
    },
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src'),
        '@services': resolve(__dirname, 'src/services'),
        '@hooks': resolve(__dirname, 'src/hooks'),
        '@router': resolve(__dirname, 'src/router'),
        '@stores': resolve(__dirname, 'src/stores'),
        '@common': resolve(__dirname, 'src/common'),
        '@components': resolve(__dirname, 'src/components'),
        '@views': resolve(__dirname, 'src/views'),
        '@utils': resolve(__dirname, 'src/utils'),
        '@helper': resolve(__dirname, 'src/helper'),
        '@types': resolve(__dirname, 'src/types'),
        '@styles': resolve(__dirname, 'src/styles'),
        '@locales': resolve(__dirname, 'src/locales'),
        '@images': resolve(__dirname, 'src/images'),
        '@public': resolve(__dirname, 'public'),
      },
      extensions: ['.tsx', '.ts', '.js'],
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
          additionalData: '@import "@styles/variables";', // 全局导入变量
        },
        css: {
          javascriptEnabled: true,
        },
      },
    },
    plugins: [
      vueJsx(),
      vue({
        script: {
          defineModel: true,
        },
      }),
      AutoImport({
      // 生成自动引入 eslintrc 配置
        eslintrc: {
          enabled: false,
          filepath: './src/types/.eslintrc-auto-import.json',
        },
        imports: ['vue', 'vue-router'], // 自动导入 vue、vue-router
        dts: './src/types/auto-imports.d.ts', // 自动导出 ts types
      }),
      viteStaticCopy({
        targets: [{
          src: 'src/images/monitoring.png',
          dest: './',
          rename: uniqueKey,
        }],
      }),
      monacoEditorPlugin({}),
      ViteHTMLEnv({
        prefix: '{{',
        suffix: '}}',
        envPrefixes: ['VITE_'],
      }),
    ].concat(isHttps ? [basicSsl()] : []),
    build: {
      sourcemap: true,
      commonjsOptions: {
        ignoreTryCatch: false,
      },
    },
    optimizeDeps: {
      exclude: ['@blueking/ip-selector/dist/vue3.x.js'],
    },
    server: {
      https: isHttps,
      port: 9999,
    },
  };
});
