<template>
  <div class="operate-item">
    <div
      class="operate-item-inner"
      @click="handleClickExport">
      <DbIcon
        class="operate-icon"
        type="daochu" />
      <span class="operate-title">{{ t('导出') }}</span>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'export'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleClickExport = () => {
    emits('export');
  };
</script>
