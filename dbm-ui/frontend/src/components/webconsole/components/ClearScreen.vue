<template>
  <div
    class="operate-item"
    @click="handleClickClearScreen">
    <div class="operate-item-inner">
      <DbIcon
        class="operate-icon"
        type="clearing" />
      <span class="operate-title">{{ t('清屏') }}</span>
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'change'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleClickClearScreen = () => {
    emits('change');
  };
</script>
