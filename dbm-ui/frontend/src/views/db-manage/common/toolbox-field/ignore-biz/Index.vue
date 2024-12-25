<template>
  <BkCheckbox
    v-model="modelValue"
    :false-label="false"
    true-label>
    <span class="safe-action-text">{{ t('忽略业务连接') }}</span>
  </BkCheckbox>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<boolean>({
    default: false,
  });
</script>

<style lang="less" scoped>
  .safe-action-text {
    padding-bottom: 2px;
    border-bottom: 1px dashed #979ba5;
  }
</style>
