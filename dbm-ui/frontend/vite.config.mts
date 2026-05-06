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
import monacoEditorPlugin from 'vite-plugin-monaco-editor';
import { viteStaticCopy } from 'vite-plugin-static-copy';

import basicSsl from '@vitejs/plugin-basic-ssl';
import vue from '@vitejs/plugin-vue';
import vueJsx from '@vitejs/plugin-vue-jsx';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd());
  const isHttps = mode === 'https';
  console.log('env === ', mode);

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
      extensions: ['.tsx', '.ts', '.js', '.mjs'],
    },
    css: {
      preprocessorOptions: {
        less: {
          javascriptEnabled: true,
          additionalData: '@import "@styles/variables";',
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
        eslintrc: {
          enabled: false,
          filepath: './src/types/.eslintrc-auto-import.json',
        },
        imports: ['vue', 'vue-router'],
        dts: './src/types/auto-imports.d.ts',
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
      monacoEditorPlugin.default({
        languageWorkers: ['editorWorkerService', 'json', 'typescript'],
      } as Parameters<typeof monacoEditorPlugin.default>[0]),
    ].concat(isHttps ? [basicSsl()] : []),
    optimizeDeps: {
      include: ['lodash-es', 'element-plus'],
    },
    build: {
      target: 'es2020',
      sourcemap: false,
      reportCompressedSize: false,
      chunkSizeWarningLimit: 2000,
      cssCodeSplit: true,
      cssMinify: 'esbuild',
      assetsInlineLimit: 0,
      modulePreload: { polyfill: false },
      rolldownOptions: {
        output: {
          codeSplitting: {
            groups: [
              { name: 'vendor-monaco', test: /node_modules\/(monaco-editor|monaco-promql)/ },
              { name: 'vendor-echarts', test: /node_modules\/echarts/ },
              { name: 'vendor-antv', test: /node_modules\/@antv/ },
              { name: 'vendor-wangeditor', test: /node_modules\/@wangeditor/ },
              { name: 'vendor-xterm', test: /node_modules\/@xterm/ },
              { name: 'vendor-xlsx', test: /node_modules\/xlsx/ },
              { name: 'vendor-sql-formatter', test: /node_modules\/sql-formatter/ },
              { name: 'vendor-element-plus', test: /node_modules\/element-plus/ },
              {
                name: 'vendor-bk-ai',
                test: /node_modules\/(@blueking\/ai-blueking|x-mavon-editor|mermaid|highlight\.js|motion-v|vue-draggable-resizable)/,
              },
              { name: 'vendor-bk-ip-selector', test: /node_modules\/@blueking\/ip-selector/ },
              { name: 'vendor-bk-tdesign', test: /node_modules\/@blueking\/tdesign-ui/ },
              { name: 'vendor-bk-table', test: /node_modules\/@blueking\/table/ },
              { name: 'vendor-bk-sub-saas', test: /node_modules\/@blueking\/sub-saas/ },
              { name: 'vendor-bk-others', test: /node_modules\/@blueking/ },
              { name: 'vendor-core', test: /node_modules/ },
            ],
          },
        },
      },
    },
    server: {
      strictPort: true,
      host: '127.0.0.1',
      allowedHosts: true,
      forwardConsole: false,
      hrm: true,
      watch: {
        usePolling: true,
      },
      port: 8088,
      proxy: {
        '/bkrepo_upload': {
          target: '', // 见获取bkrepo上传凭证接口
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/bkrepo_upload/, ''),
        },
      },
    },
    preview: {
      port: 8088,
    },
  };
});
