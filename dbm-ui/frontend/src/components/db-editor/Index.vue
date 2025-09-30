<template>
  <div
    v-if="isEditorMode"
    class="db-editor-main">
    <Toolbar
      :default-config="toolbarConfig"
      :editor="editorRef"
      :mode="mode"
      style="border-bottom: 1px solid #dcdee5" />
    <Editor
      v-model="editorHtml"
      :default-config="editorConfig"
      :mode="mode"
      :style="{ height: `${editorHeight}px` }"
      @on-created="handleCreated" />
  </div>
  <div
    v-else
    v-bk-xss-html="editorHtml"
    class="editor-content-view"></div>
</template>
<script setup lang="ts">
  import Cookies from 'js-cookie';

  import { t } from '@locales/index';

  import '@wangeditor/editor/dist/css/style.css';
  import { Editor, Toolbar } from '@wangeditor/editor-for-vue';

  interface Props {
    editMode?: 'default' | 'viewer';
    editorHeight?: number;
    excludeKeys?: string[];
    placeholder?: string;
    uploadImageConfig?: any;
  }

  const props = withDefaults(defineProps<Props>(), {
    editMode: 'default',
    editorHeight: 320,
    excludeKeys: () => [
      '|',
      'group-more-style',
      'bgColor',
      'fontFamily',
      'fontSize',
      'lineHeight',
      'todo',
      'group-indent',
      'uploadVideo',
      'emotion',
      'insertTable',
      'color',
      'group-video',
    ],
    placeholder: t('请输入内容...'),
    // 其他上传图片配置见 wangeditor 文档
    uploadImageConfig: () => ({}),
  });

  // 内容 HTML
  const editorHtml = defineModel<string>({
    default: '',
  });

  // 编辑器实例，必须用 shallowRef
  const editorRef = shallowRef();

  const isEditorMode = computed(() => props.editMode === 'default');
  const editorConfig = computed(() => ({
    MENU_CONF: {
      uploadImage: {
        customInsert(res: any, insertFn: any) {
          insertFn(res.data.url);
        },
        headers: {
          'X-CSRFToken': Cookies.get('dbm_csrftoken'),
        },
        withCredentials: true,
        ...props.uploadImageConfig,
      },
    },
    placeholder: props.placeholder,
  }));

  const toolbarConfig = computed(() => ({
    excludeKeys: props.excludeKeys,
  }));

  const mode = 'default';

  const handleCreated = (editor: any) => {
    editorRef.value = editor; // 记录 editor 实例，必须！
  };

  // 组件销毁时，也及时销毁编辑器
  onBeforeUnmount(() => {
    const editor = editorRef.value;
    if (editor == null) return;
    editor.destroy();
  });
</script>
<style lang="less">
  .db-editor-main {
    border: 1px solid #dcdee5;
    border-radius: 2px;

    &.w-e-full-screen-container {
      z-index: 999;
    }
  }

  .editor-content-view {
    background: #f5f7fa;
    border-radius: 8px;
    padding: 16px;
    position: relative;
    font-family: MicrosoftYaHei;
    color: #313238;
  }

  .editor-content-view p,
  .editor-content-view li {
    white-space: pre-wrap; /* 保留空格 */
  }

  .editor-content-view blockquote {
    border-left: 8px solid #d0e5f2;
    padding: 10px 10px;
    margin: 10px 0;
    background-color: #f1f1f1;
  }

  .editor-content-view code {
    font-family: monospace;
    background-color: #eee;
    padding: 3px;
    border-radius: 3px;
  }
  .editor-content-view pre > code {
    display: block;
    padding: 10px;
  }

  .editor-content-view table {
    border-collapse: collapse;
  }
  .editor-content-view td,
  .editor-content-view th {
    border: 1px solid #ccc;
    min-width: 50px;
    height: 20px;
  }
  .editor-content-view th {
    background-color: #f1f1f1;
  }

  .editor-content-view ul,
  .editor-content-view ol {
    padding-left: 20px;
  }

  .editor-content-view input[type='checkbox'] {
    margin-right: 5px;
  }

  .edit-follow-up {
    .operate-btn-main {
      margin-top: 12px;
      display: flex;
      gap: 8px;
    }
  }
</style>
