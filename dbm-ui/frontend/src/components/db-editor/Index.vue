<template>
  <div
    ref="editorWraperRef"
    class="db-editor-main"
    :class="{ 'is-readonly': !isEditorMode }">
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

  const editorWraperRef = ref<HTMLDivElement>();

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

  watch(
    isEditorMode,
    () => {
      setTimeout(() => {
        if (isEditorMode.value) {
          editorRef.value?.focus(true);
        } else {
          editorRef.value?.disable();
        }
      });
    },
    { immediate: true },
  );

  const handleCreated = (editor: any) => {
    editorRef.value = editor; // 记录 editor 实例，必须！
  };

  // 组件销毁时，也及时销毁编辑器
  onBeforeUnmount(() => {
    editorRef.value?.destroy();
  });
</script>
<style lang="less">
  .db-editor-main {
    border: 1px solid #dcdee5;
    border-radius: 2px;

    &.w-e-full-screen-container {
      z-index: 999;
    }

    &.is-readonly {
      padding: 0;

      [id^='w-e-element'] {
        margin: 0;
      }

      div[id^='w-e-textarea'] {
        padding: 0;
      }

      div[data-w-e-toolbar='true'] {
        display: none;
      }

      div[data-w-e-textarea='true'] {
        height: auto !important;
      }

      .w-e-text-container {
        background: transparent;
      }
    }
  }

  .edit-follow-up {
    .operate-btn-main {
      margin-top: 12px;
      display: flex;
      gap: 8px;
    }
  }
</style>
