<template>
  <DbEditor
    v-model="editorHtml"
    :placeholder="placeholder"
    :readonly="readonly"
    :upload-image-config="uploadImageConfig" />
</template>
<script setup lang="ts">
  import DbEditor from '@components/db-editor/Index.vue';

  interface Props {
    placeholder?: string;
    readonly?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    placeholder: undefined,
    readonly: false,
  });

  const editorHtml = defineModel<string>({
    default: '',
  });

  const uploadImageConfig = {
    fieldName: 'file',
    meta: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    },
    server: '/apis/risk_memo/images/',
  };
</script>
