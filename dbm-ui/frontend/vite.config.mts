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

  // vite-plugin-monaco-editor 通过 transformIndexHtml 注入 MonacoEnvironment，
  // index.html 经 viteStaticCopy 原样输出不经过该钩子，这里按插件同款模板补齐（javascript 与 typescript 共享 worker）
  // worker 产物落在 outDir 的 base 子目录下，路径经 __loadAssetsUrl__ 运行时拼接以跟随 BK_STATIC_URL
  const monacoWorkerDir = [(env.VITE_PUBLIC_PATH ?? '').replace(/^\/+|\/+$/g, ''), 'monacoeditorwork']
    .filter(Boolean)
    .join('/');
  const monacoWorkerPath = (name: string) =>
    `window.__loadAssetsUrl__(${JSON.stringify(`${monacoWorkerDir}/${name}`)})`;
  const monacoWorkerPaths = `{
  "editorWorkerService": ${monacoWorkerPath('editor.worker.bundle.js')},
  "json": ${monacoWorkerPath('json.worker.bundle.js')},
  "typescript": ${monacoWorkerPath('ts.worker.bundle.js')},
  "javascript": ${monacoWorkerPath('ts.worker.bundle.js')}
}`;
  const monacoEnvironmentScript = `<script>self["MonacoEnvironment"] = (function (paths) {
          return {
            globalAPI: false,
            getWorkerUrl : function (moduleId, label) {
              var result =  paths[label];
              if (/^((http:)|(https:)|(file:)|(\\/\\/))/.test(result)) {
                var currentUrl = String(window.location);
                var currentOrigin = currentUrl.substr(0, currentUrl.length - window.location.hash.length - window.location.search.length - window.location.pathname.length);
                if (result.substring(0, currentOrigin.length) !== currentOrigin) {
                  var js = '/*' + label + '*/importScripts("' + result + '");';
                  var blob = new Blob([js], { type: 'application/javascript' });
                  return URL.createObjectURL(blob);
                }
              }
              return result;
            }
          };
        })(${monacoWorkerPaths});</script>`;

  return {
    base: env.VITE_PUBLIC_PATH,
    // 项目不使用 index.html 作为构建入口（入口由页面内 manifest 加载器运行时加载），顶层 input 在 dev/build/optimizer 间共享
    input: {
      main: resolve(import.meta.dirname, 'src/main.ts'),
    },
    resolve: {
      alias: {
        '@': resolve(import.meta.dirname, 'src'),
        '@services': resolve(import.meta.dirname, 'src/services'),
        '@hooks': resolve(import.meta.dirname, 'src/hooks'),
        '@router': resolve(import.meta.dirname, 'src/router'),
        '@stores': resolve(import.meta.dirname, 'src/stores'),
        '@common': resolve(import.meta.dirname, 'src/common'),
        '@components': resolve(import.meta.dirname, 'src/components'),
        '@views': resolve(import.meta.dirname, 'src/views'),
        '@utils': resolve(import.meta.dirname, 'src/utils'),
        '@helper': resolve(import.meta.dirname, 'src/helper'),
        '@types': resolve(import.meta.dirname, 'src/types'),
        '@styles': resolve(import.meta.dirname, 'src/styles'),
        '@locales': resolve(import.meta.dirname, 'src/locales'),
        '@images': resolve(import.meta.dirname, 'src/images'),
        '@lib': resolve(import.meta.dirname, 'lib'),
        '@patch': resolve(import.meta.dirname, 'patch'),
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
            // index.html 由后端模板渲染下发，不作为构建输入避免注入入口标签，入口由页面内 manifest 加载器运行时加载
            src: 'index.html',
            dest: './',
            transform: (content: string) =>
              content
                // 注入到 head 末尾，确保排在 __loadAssetsUrl__ 定义之后
                .replace('</head>', `  ${monacoEnvironmentScript}\n  </head>`)
                .replace(/\s*<script\s+type="module"\s+src="\/src\/main\.ts"><\/script>/, '')
                .replaceAll('%VITE_AJAX_URL_PREFIX%', env.VITE_AJAX_URL_PREFIX ?? '')
                .replaceAll('%VITE_ROUTER_PERFIX%', env.VITE_ROUTER_PERFIX ?? ''),
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
      assetsInlineLimit: 0,
      modulePreload: { polyfill: false },
      manifest: true,
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
    experimental: {
      renderBuiltUrl(filename, { hostType }) {
        if (hostType === 'js') {
          return { runtime: `window.__loadAssetsUrl__(${JSON.stringify(filename)})` };
        }
        return { relative: true };
      },
    },
    server: {
      strictPort: true,
      host: '127.0.0.1',
      allowedHosts: true,
      forwardConsole: false,
      hmr: true,
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
