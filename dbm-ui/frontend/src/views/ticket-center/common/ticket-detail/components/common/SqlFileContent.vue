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
  <div
    ref="rootRef"
    class="ticket-import-sql-file-render">
    <div class="editor-layout-header">
      <span>{{ getSQLFilename(title) }}</span>
      <div class="editro-action-box">
        <DbIcon
          type="arrow-down"
          @click="handleDownload" />
        <DbIcon
          v-if="isFullscreen"
          type="un-full-screen"
          @click="handleExitFullScreen" />
        <DbIcon
          v-else
          type="full-screen"
          @click="handleFullScreen" />
      </div>
    </div>
    <!-- 2. 中间编辑器区域 — 弹性填充 -->
    <div
      ref="editorRef"
      class="editor-main-area" />

    <!-- 3. 底部检查结果面板 — 可向上弹出/收起 -->
    <RenderMessageList
      class="editor-result-panel"
      :data="messageList"
      @goto-line="handleGotoLine" />
  </div>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';
  import screenfull from 'screenfull';

  import { getSQLFilename } from '@utils';

  import RenderMessageList, { type IMessageList } from './MessageList.vue';

  interface GrammarCheckInfo {
    bancommand_warnings: {
      command_type: string;
      line: number;
      sqltext: string;
      warn_info: string;
    }[];
    highrisk_warnings: {
      command_type: string;
      line: number;
      sqltext: string;
      warn_info: string;
    }[];
    syntax_fails: {
      command_type: string;
      line: number;
      sqltext: string;
      warn_info: string;
    }[];
  }

  interface Props {
    grammarCheckInfo?: GrammarCheckInfo;
    modelValue: string;
    readonly?: boolean;
    title: string;
  }

  interface Emits {
    (e: 'update:modelValue', value: string): void;
    (e: 'change', value: string): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    grammarCheckInfo: () => ({
      bancommand_warnings: [],
      highrisk_warnings: [],
      syntax_fails: [],
    }),
    readonly: false,
  });

  const emits = defineEmits<Emits>();

  // 从 grammarCheckInfo 直接计算 messageList
  const messageList = computed<IMessageList>(() => {
    const result: IMessageList = [];
    const grammarCheckInfo = props.grammarCheckInfo;

    if (!grammarCheckInfo) {
      return result;
    }

    // syntax_fails -> error
    if (grammarCheckInfo.syntax_fails) {
      grammarCheckInfo.syntax_fails.forEach((item) => {
        result.push({
          category: 'syntax_error',
          line: item.line,
          message: item.warn_info,
          type: 'error',
        });
      });
    }

    // bancommand_warnings -> error
    if (grammarCheckInfo.bancommand_warnings) {
      grammarCheckInfo.bancommand_warnings.forEach((item) => {
        result.push({
          category: 'ban_command',
          line: item.line,
          message: item.warn_info,
          type: 'error',
        });
      });
    }

    // highrisk_warnings -> warning
    if (grammarCheckInfo.highrisk_warnings) {
      grammarCheckInfo.highrisk_warnings.forEach((item) => {
        result.push({
          category: 'high_risk',
          line: item.line,
          message: item.warn_info,
          type: 'warning',
        });
      });
    }

    return result;
  });

  const rootRef = ref();
  const editorRef = ref();
  const isFullscreen = ref(false);

  let editor: monaco.editor.IStandaloneCodeEditor;
  let highlightDecoration: string[] = [];
  let issueDecorations: string[] = [];

  // 根据消息列表动态设置错误/警告行装饰
  watch(
    messageList,
    (list) => {
      if (!editor) return;
      const model = editor.getModel();
      if (!model) return;

      // 清除旧装饰
      issueDecorations = editor.deltaDecorations(issueDecorations, []);

      if (list.length === 0) return;

      const decorations: monaco.editor.IModelDeltaDecoration[] = [];
      const lineCount = model.getLineCount();
      list.forEach((item) => {
        if (!Number.isInteger(item.line) || item.line < 1 || item.line > lineCount) return;
        const maxCol = model.getLineMaxColumn(item.line);

        if (item.type === 'error') {
          decorations.push({
            options: {
              className: 'editor-line-error',
              glyphMarginHoverMessage: { value: item.message },
              isWholeLine: true,
              lineNumberClassName: 'editor-line-no-error',
              overviewRuler: { color: '#ea3636', position: monaco.editor.OverviewRulerLane.Left },
            },
            range: new monaco.Range(item.line, 1, item.line, maxCol),
          });
        } else if (item.type === 'warning') {
          decorations.push({
            options: {
              glyphMarginHoverMessage: { value: item.message },
              isWholeLine: true,
              lineNumberClassName: 'editor-line-no-warn',
              overviewRuler: { color: '#ffb648', position: monaco.editor.OverviewRulerLane.Left },
            },
            range: new monaco.Range(item.line, 1, item.line, maxCol),
          });
        }
      });

      issueDecorations = editor.deltaDecorations([], decorations);
    },
    { deep: true },
  );

  watch(
    () => props.modelValue,
    () => {
      setTimeout(() => {
        if (props.modelValue !== editor.getValue()) {
          editor.setValue(props.modelValue || '');
        }
      });
    },
    {
      immediate: true,
    },
  );

  const handleToggleScreenfull = () => {
    if (screenfull.isFullscreen) {
      isFullscreen.value = true;
    } else {
      isFullscreen.value = false;
    }
    editor.layout();
  };

  const handleReize = () => {
    editor.layout();
  };

  const handleDownload = () => {
    const link = document.createElement('a');
    link.download = `${props.title.replace(/\s/g, '')}.sql`;
    link.style.display = 'none';
    // 字符内容转变成blob地址
    const blob = new Blob([props.modelValue], { type: 'sql' });
    link.href = URL.createObjectURL(blob);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleFullScreen = () => {
    screenfull.toggle(rootRef.value);
  };

  const handleExitFullScreen = () => {
    screenfull.toggle(rootRef.value);
  };

  const handleGotoLine = (line: number) => {
    if (!editor) return;
    // 移除旧的高亮
    if (highlightDecoration.length > 0) {
      editor.deltaDecorations(highlightDecoration, []);
    }
    // 定位到目标行
    const model = editor.getModel();
    if (!model) return;
    if (!Number.isInteger(line) || line < 1 || line > model.getLineCount()) return;
    editor.revealLineInCenter(line);
    // 添加高亮装饰
    highlightDecoration = editor.deltaDecorations(
      [],
      [
        {
          options: {
            className: 'editor-line-highlight',
            isWholeLine: true,
            lineNumberClassName: 'editor-line-no-highlight',
          },
          range: new monaco.Range(line, 1, line, model.getLineMaxColumn(line)),
        },
      ],
    );
    editor.focus();
  };

  onMounted(() => {
    editor = monaco.editor.create(editorRef.value, {
      automaticLayout: true,
      language: 'sql',
      lineNumbersMinChars: 3,
      minimap: {
        enabled: false,
      },
      readOnly: props.readonly,
      renderLineHighlight: 'none',
      scrollbar: {
        alwaysConsumeMouseWheel: false,
      },
      theme: 'vs-dark',
      wordWrap: 'on',
    });
    editor.onDidChangeModelContent(() => {
      const value = editor.getValue();
      emits('update:modelValue', value);
      emits('change', value);
    });
    screenfull.on('change', handleToggleScreenfull);
    window.addEventListener('resize', handleReize);
  });

  onBeforeUnmount(() => {
    editor.dispose();
    screenfull.off('change', handleToggleScreenfull);
    window.removeEventListener('resize', handleReize);
  });
</script>
<style lang="less">
  .ticket-import-sql-file-render {
    display: flex;
    flex-direction: column;
    z-index: 0;
    height: calc(100vh - 80px);
    overflow: hidden;

    .editor-layout-header {
      display: flex;
      flex-shrink: 0;
      align-items: center;
      height: 40px;
      padding-right: 16px;
      padding-left: 25px;
      font-size: 14px;
      color: #c4c6cc;
      background: #2e2e2e;

      .editro-action-box {
        margin-left: auto;
        color: #979ba5;
        flex-shrink: 0;
        display: flex;
        align-items: center;

        & > * {
          margin-left: 12px;
          cursor: pointer;
        }
      }
    }

    /* ===== 2. 中间编辑器区域 — 弹性填充 ===== */
    .editor-main-area {
      flex: 1;
      min-height: 0;
      overflow: hidden;
      background: #1e1e1e;
    }

    /* ===== 3. 底部检查结果面板 — 向上弹出/收起 ===== */
    .editor-result-panel {
      flex-shrink: 0;
      border-top: 1px solid #2d2d2d;
      max-height: 280px;
      min-width: 0;
      overflow-x: hidden;
      background: #252526;
    }
  }
</style>
<style lang="less">
  /* === 错误行：红色行号 + 红色波浪下划线 === */
  .editor-line-no-error {
    color: #ff5757 !important;
    font-weight: 600;
  }

  .editor-line-error {
    &::after {
      content: '';
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 2px;
      background: repeating-linear-gradient(-45deg, transparent, transparent 3px, #f48771 3px, #f48771 4px);
    }
  }

  /* === 警告行：黄色行号 === */
  .editor-line-no-warn {
    color: #ffb648 !important;
  }

  /* === 点击高亮行：黄色背景 + 左侧竖线 + 闪动动画 === */
  .editor-line-highlight {
    background-color: rgba(255, 220, 100, 0.18) !important;
    box-shadow: inset 3px 0 0 0 #ffd54f;

    animation: lineFlash 1.2s ease-out;
  }

  .editor-line-no-highlight {
    color: #ffd54f !important;
    font-weight: 600;
  }

  @keyframes lineFlash {
    0% {
      background-color: rgba(255, 220, 100, 0.55);
    }
    40% {
      background-color: rgba(255, 220, 100, 0.55);
    }
    100% {
      background-color: rgba(255, 220, 100, 0.18);
    }
  }
</style>
