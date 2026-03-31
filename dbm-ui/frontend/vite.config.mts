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
    ].concat(isHttps ? [basicSsl()] : []),
    build: {
      target: 'es2020',
      sourcemap: false,
      reportCompressedSize: false,
      chunkSizeWarningLimit: 2000,
      minify: 'esbuild',
      cssCodeSplit: true,
      cssMinify: 'esbuild',
      assetsInlineLimit: 0,
      modulePreload: { polyfill: false },
      esbuild: {
        legalComments: 'none',
        lineLimit: 200,
      },
      rollupOptions: {
        maxParallelFileOps: 5,
        output: {
          manualChunks(id) {
            if (!id.includes('node_modules')) {
              return undefined;
            }

            if (id.includes('monaco-editor') || id.includes('monaco-promql')) return 'vendor-monaco';
            if (id.includes('echarts')) return 'vendor-echarts';
            if (id.includes('@antv')) return 'vendor-antv';
            if (id.includes('@wangeditor')) return 'vendor-wangeditor';
            if (id.includes('@xterm')) return 'vendor-xterm';
            if (id.includes('xlsx')) return 'vendor-xlsx';
            if (id.includes('sql-formatter')) return 'vendor-sql-formatter';
            if (id.includes('element-plus')) return 'vendor-element-plus';

            // ai-blueking 及其专属提升依赖归为同一 chunk，避免与 vendor-core 循环
            if (
              id.includes('@blueking/ai-blueking') ||
              id.includes('x-mavon-editor') ||
              id.includes('mermaid') ||
              id.includes('highlight.js') ||
              id.includes('motion-v') ||
              id.includes('vue-draggable-resizable')
            ) {
              return 'vendor-bk-ai';
            }

            if (id.includes('@blueking/ip-selector')) return 'vendor-bk-ip-selector';
            if (id.includes('@blueking/tdesign-ui')) return 'vendor-bk-tdesign';
            if (id.includes('@blueking/table')) return 'vendor-bk-table';
            if (id.includes('@blueking/sub-saas')) return 'vendor-bk-sub-saas';
            if (id.includes('@blueking')) return 'vendor-bk-others';

            return 'vendor-core';
          },
        },
      },
    },
    server: {
      strictPort: true,
      host: '127.0.0.1',
      allowedHosts: true,
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
