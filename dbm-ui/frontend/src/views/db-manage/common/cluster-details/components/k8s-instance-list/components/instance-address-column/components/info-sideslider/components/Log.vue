<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="k8s-instance-column-sideslider-log">
    <BkLoading
      :loading="isLoading"
      style="height: 100%">
      <!-- <div class="content-top">
        <BkSelect
          v-model="formData.time"
          :list="timeList"
          :popover-min-width="200"
          @change="handleTimeChange">
          <template #trigger="{ selected }">
            <div class="time-trigger">
              <DbIcon
                class="tigger-icon ml-4 mr-4"
                type="date-line" />
              <div>{{ selected?.[0]?.label || '' }}</div>
            </div>
          </template>
        </BkSelect>
        <BkInput
          v-model="formData.searchKey"
          class="search-input ml-12"
          clearable
          :placeholder="t('搜索关键字')"
          type="search"
          @clear="handleSearchKeyClear"
          @enter="handleSearchKeyEnter" />
      </div> -->
      <div
        ref="editorRef"
        class="editor-container"
        :style="{ height: `${height}px` }" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  // import dayjs from 'dayjs';
  import * as monaco from 'monaco-editor';
  // import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getPodLog } from '@services/source/kubernetesToolbox';

  import { useUserProfile } from '@stores';

  import { getOffset } from '@utils';

  interface Props {
    clusterData: {
      cluster_name: string;
      db_type: string;
      k8s_cluster_name: string;
      namespace: string;
    };
    podName: string;
    role: string;
  }

  const props = defineProps<Props>();

  // const { t } = useI18n();
  const userProfile = useUserProfile();

  // const timeList = [
  //   {
  //     label: t('最近 1 小时'),
  //     value: [dayjs().subtract(1, 'hour'), dayjs()],
  //   },
  //   {
  //     label: t('最近 12 小时'),
  //     value: [dayjs().subtract(12, 'hour'), dayjs()],
  //   },
  //   {
  //     label: t('今天'),
  //     value: [dayjs().startOf('day'), dayjs().endOf('day')],
  //   },
  //   {
  //     label: t('最近 7 天'),
  //     value: [dayjs().subtract(6, 'day').startOf('day'), dayjs().endOf('day')],
  //   },
  //   {
  //     label: t('最近 1 个月'),
  //     value: [dayjs().subtract(1, 'month').startOf('day'), dayjs().endOf('day')],
  //   },
  //   {
  //     label: t('最近 3 个月'),
  //     value: [dayjs().subtract(3, 'month').startOf('day'), dayjs().endOf('day')],
  //   },
  //   {
  //     label: t('最近 6 个月'),
  //     value: [dayjs().subtract(6, 'month').startOf('day'), dayjs().endOf('day')],
  //   },
  // ].map((item) => ({
  //   ...item,
  //   value: item.value.map((date) => date.format('YYYY-MM-DDTHH:mm:ss')).join(','),
  // }));

  const editorRef = ref();
  // const formData = ref({
  //   searchKey: '',
  //   time: timeList[3].value,
  // });
  const height = ref(500);

  let editor: monaco.editor.IStandaloneCodeEditor;
  let decorationsCollection: monaco.editor.IEditorDecorationsCollection | null = null;

  const { loading: isLoading, run: getLogs } = useRequest(getPodLog, {
    manual: true,
    onSuccess(logResult) {
      const formattedLogs = logResult.result.map((item) => item.message);
      editor.setValue(formattedLogs.join('\n'));
      // highlightLinesByLevel(editor, formattedLogs);
      // const formattedLogs = logResult.result.map((item) => `${item.timestamp} ${item.message}`).join('\n');
      // editor.setValue(formattedLogs);
    },
  });

  // const formatLogs = (logs: Array<{ message: string; timestamp: string }>) =>
  //   logs.map((log) => {
  //     try {
  //       const parsed = JSON.parse(lzog.message) as { caller?: string; level?: string; msg?: string };
  //       const level = (parsed.level || 'unknown').toUpperCase();
  //       const msg = parsed.msg || '';
  //       const timestamp = utcDisplayTime(log.timestamp);
  //       return `[${timestamp}] [${level}]${msg}`;
  //     } catch {
  //       return log.message;
  //     }
  //   });

  // 添加/更新行背景色
  // const highlightLinesByLevel = (editor: monaco.editor.IStandaloneCodeEditor, logs: string[]): void => {
  //   if (!decorationsCollection) {
  //     decorationsCollection = editor.createDecorationsCollection();
  //   }

  //   const newDecorations: monaco.editor.IModelDeltaDecoration[] = [];

  //   logs.forEach((log, index) => {
  //     const lineNum = index + 1;

  //     if (log.includes('[WARN]')) {
  //       newDecorations.push({
  //         options: {
  //           className: 'warn-line',
  //           isWholeLine: true,
  //         },
  //         range: new monaco.Range(lineNum, 1, lineNum, 1),
  //       });
  //     } else if (log.includes('[ERROR]')) {
  //       newDecorations.push({
  //         options: {
  //           className: 'error-line',
  //           isWholeLine: true,
  //         },
  //         range: new monaco.Range(lineNum, 1, lineNum, 1),
  //       });
  //     }
  //   });

  //   // 直接设置装饰器集合
  //   decorationsCollection.set(newDecorations);
  // };

  watch(
    () => [props.role, props.podName],
    () => {
      fetchData();
    },
  );

  const registerLogHighlighter = (): void => {
    // 注册语言
    monaco.languages.register({ id: 'structured-log' });

    // 定义语法规则
    monaco.languages.setMonarchTokensProvider('structured-log', {
      tokenizer: {
        root: [
          // 匹配时间戳
          [/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z/, 'log-timestamp'],
          // 匹配日志级别：INFO, WARN, ERROR, DEBUG, TRACE
          [/\s(INFO)\s/, { cases: { $1: 'log-info' } }],
          [/\s(WARN)\s/, { cases: { $1: 'log-warn' } }],
          [/\s(ERROR)\s/, { cases: { $1: 'log-error' } }],
          [/\s(DEBUG|TRACE)\s/, 'log-debug'],
          // 匹配模块路径：xxx::xxx: 格式（如 actix_web::middleware::logger:）
          [/[a-zA-Z_]\w*(?:::[a-zA-Z_]\w*)+:/, 'log-module'],
        ],
      },
    });

    // 定义主题颜色
    monaco.editor.defineTheme('log-theme', {
      base: 'vs-dark',
      colors: { 'editor.background': '#1E1E1E' },
      inherit: true,
      rules: [
        { foreground: '#858585', token: 'log-timestamp' }, // 时间灰色
        { foreground: '2dcb56', token: 'log-info' }, // INFO绿色
        { foreground: '#ff9c01', token: 'log-warn' }, // WARN黄色
        { foreground: '#ea3636', token: 'log-error' }, // ERROR红色
        // { foreground: '#858585', token: 'log-debug' }, // DEBUG/TRACE灰色
        { foreground: '#858585', token: 'log-module' }, // 模块路径灰色
      ],
    });
  };

  const fetchData = () => {
    // const { searchKey, time } = formData.value;
    // const [startTime, endTime] = time.split(',');

    getLogs({
      bk_username: userProfile.username,
      clusterName: props.clusterData.cluster_name,
      componentName: props.role,
      // container: props.clusterData.db_type.replace('k8s_', ''),
      container: props.role,
      // endTime: endTime,
      k8sClusterName: props.clusterData.k8s_cluster_name,
      limit: -1,
      namespace: props.clusterData.namespace,
      offset: 0,
      podName: props.podName,
      // search_key: searchKey || undefined,
      // startTime: startTime,
    });
  };

  // const handleTimeChange = () => {
  //   fetchData();
  // };

  // const handleSearchKeyClear = () => {
  //   fetchData();
  // };

  // const handleSearchKeyEnter = () => {
  //   fetchData();
  // };

  onMounted(() => {
    height.value = window.innerHeight - getOffset(editorRef.value as HTMLElement).top - 24;
  });

  onMounted(() => {
    fetchData();

    nextTick(() => {
      registerLogHighlighter();

      editor = monaco.editor.create(editorRef.value, {
        automaticLayout: true,
        language: 'structured-log', // 使用自定义语言
        lineHeight: 24,
        minimap: {
          enabled: false,
        },
        padding: {
          bottom: 20, // 底部内边距（像素）
          top: 20, // 顶部内边距（像素）
        },
        readOnly: true,
        renderLineHighlight: 'none',
        scrollbar: {
          alwaysConsumeMouseWheel: false,
        },
        theme: 'log-theme', // 使用自定义主题
        wordWrap: 'on',
      });

      decorationsCollection = editor.createDecorationsCollection();

      // 单独给每行加左内边距
      // const style = document.createElement('style');
      // style.textContent = `
      //   .monaco-editor .view-line {
      //     padding-left: 12px !important;
      //   }
      // `;
      // document.head.appendChild(style);
    });
  });

  onBeforeUnmount(() => {
    editor.dispose();
    if (decorationsCollection) {
      decorationsCollection.clear();
    }
  });
</script>

<style lang="less">
  .k8s-instance-column-sideslider-log {
    .content-top {
      display: flex;
      width: 100%;
      padding: 12px;
      background: #242424;
      box-shadow: 0 2px 4px 0 #00000029;
      align-items: center;

      .bk-select-trigger {
        &:hover {
          background-color: #fff3;
        }
      }

      .time-trigger {
        display: flex;
        width: 160px;
        height: 33px;
        color: #b3b3b3;
        cursor: pointer;
        background-color: #ffffff1a;
        border: 1px solid #2e2e2e;
        border-radius: 2px;
        align-items: center;

        .tigger-icon {
          font-size: 16px;
        }
      }

      .search-input {
        width: 400px;
        border-color: #ffffff1a;

        input {
          color: #b3b3b3;
          background: #ffffff1a;
          border-radius: 2px;
        }

        .bk-input--suffix-icon {
          background: #ffffff1a;

          &:hover {
            color: #c4c6cc;
          }
        }
      }
    }

    .editor-container {
      .warn-line {
        background-color: rgb(255 156 1 / 6%);
        border-left: 3px solid #ff9c01;
      }

      .error-line {
        background-color: rgb(244 71 71 / 8%);
        border-left: 3px solid #ea3636;
      }
    }
  }
</style>
