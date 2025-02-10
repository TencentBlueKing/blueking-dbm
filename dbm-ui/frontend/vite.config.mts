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
import ViteHTMLEnv from 'vite-plugin-html-env';
import monacoEditorPlugin from 'vite-plugin-monaco-editor';
import { viteStaticCopy } from 'vite-plugin-static-copy';

import basicSsl from '@vitejs/plugin-basic-ssl';
import vue from '@vitejs/plugin-vue';
import vueJsx from '@vitejs/plugin-vue-jsx';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  const isHttps = mode === 'https';

  return {
    base: env.VITE_PUBLIC_PATH,
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
        '@lib': resolve(__dirname, 'lib'),
        '@patch': resolve(__dirname, 'patch'),
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
        targets: [
          {
            src: 'src/images/monitoring.png',
            dest: './',
          },
          {
            src: 'lib',
            dest: './',
          },
        ],
      }),
      monacoEditorPlugin.default({}),
      ViteHTMLEnv({
        prefix: '{{',
        suffix: '}}',
        envPrefixes: ['VITE_'],
      }),
    ].concat(isHttps ? [basicSsl()] : []),
    optimizeDeps: {
      exclude: ['@blueking/ip-selector/dist/vue3.x.js'],
    },
    server: {
      strictPort: true,
      host: '127.0.0.1',
      allowedHosts: true,
      port: 8088,
      proxy: {
        '/bkrepo_upload': {
          target: '', // 见获取bkrepo上传凭证接口
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/bkrepo_upload/, ''),
        },
      },
    },
  };
});
