<template>
  <div
    ref="edtorMainRef"
    class="params-editor-main">
    <div class="editor-header">
      <div class="title">{{ title }}</div>
      <div class="operations">
        <DbIcon
          class="icon"
          type="copy"
          @click="handleClickCopy" />
        <DbIcon
          class="icon"
          :type="isFullscreen ? 'un-full-screen' : 'full-screen'"
          @click="handleToggle" />
      </div>
    </div>
    <div
      ref="editorRef"
      class="editor-main"
      :class="{ 'editor-main-fullscreen': isFullscreen }" />
  </div>
</template>
<script setup lang="ts">
  import * as monaco from 'monaco-editor';

  import { execCopy } from '@utils';

  import { useFullscreen } from '@vueuse/core';

  interface Props {
    data?: string;
    title?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    title: '',
  });

  const edtorMainRef = ref();
  const editorRef = ref();

  const { isFullscreen, toggle } = useFullscreen(edtorMainRef);

  let editor: monaco.editor.IStandaloneCodeEditor;

  watch(
    () => props.data,
    () => {
      if (props.data) {
        setTimeout(() => {
          editor?.setValue(props.data);
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleClickCopy = () => {
    execCopy(props.data);
  };

  const handleToggle = () => {
    toggle();
    setTimeout(() => {
      editor?.layout();
    });
  };

  onMounted(() => {
    editor = monaco.editor.create(editorRef.value, {
      automaticLayout: true,
      fontSize: 13,
      language: 'json',
      lineNumbersMinChars: 3,
      minimap: {
        enabled: false,
      },
      readOnly: true,
      renderLineHighlight: 'none',
      scrollbar: {
        alwaysConsumeMouseWheel: false,
      },
      theme: 'vs-dark',
      wordWrap: 'bounded',
    });
  });

  onBeforeUnmount(() => {
    editor?.dispose();
  });
</script>
<style lang="less">
  .params-editor-main {
    .editor-header {
      display: flex;
      align-items: center;
      height: 40px;
      background: #242424;
      border-radius: 2px 2px 0 0;

      .title {
        margin-left: 25px;
        font-size: 14px;
        color: #c4c6cc;
      }

      .operations {
        display: flex;
        margin-left: auto;

        .icon {
          margin-right: 18px;
          font-size: 12px;
          color: #979ba5;
          cursor: pointer;
        }
      }
    }

    .editor-main {
      width: 100%;
      height: 100%;
      height: 320px;
      max-height: 600px;

      &.editor-main-fullscreen {
        height: calc(100vh - 40px);
        max-height: calc(100vh - 40px);
      }
    }
  }
</style>
