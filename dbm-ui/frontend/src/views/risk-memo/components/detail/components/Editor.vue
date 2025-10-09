<template>
  <DbEditor
    v-model="editorHtml"
    :edit-mode="mode"
    :upload-image-config="uploadImageConfig" />
</template>
<script setup lang="ts">
  import DbEditor from '@components/db-editor/Index.vue';

  interface Props {
    mode?: 'default' | 'viewer';
  }

  withDefaults(defineProps<Props>(), {
    mode: 'default',
  });

  const editorHtml = defineModel({
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
