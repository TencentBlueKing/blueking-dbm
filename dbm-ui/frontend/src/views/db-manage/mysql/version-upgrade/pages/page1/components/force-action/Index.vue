<template>
  <div class="force-action">
    <BkCheckbox
      v-model="modelValue"
      v-bk-tooltips="t('如忽略，有连接的情况下也会执行强制升级')">
      <span class="force-action-text">{{ t('忽略业务连接') }}</span>
    </BkCheckbox>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const modelValue = defineModel<boolean>({
    required: true,
  });

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .force-action {
    margin-top: 20px;

    .force-action-text {
      padding-bottom: 2px;
      border-bottom: 1px dashed #979ba5;
    }
  }
</style>
