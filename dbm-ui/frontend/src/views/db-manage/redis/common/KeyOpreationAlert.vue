<template>
  <BkAlert
    class="key-opration-alert-info"
    closable>
    <div class="alert-info-item">
      <span class="alert-info-label">{{ t('可使用通配符进行提取_如_Key或Key') }}</span>
      <span class="alert-info-value">{{ t('提取以Key开头的key_包括Key') }}</span>
    </div>
    <div class="alert-info-item">
      <span class="alert-info-label">*Key$ :</span>
      <span class="alert-info-value">{{ t('提取以Key结尾的key_包括Key') }}</span>
    </div>
    <div class="alert-info-item">
      <span class="alert-info-label">^Key$ :</span>
      <span class="alert-info-value">{{ t('提取精确匹配的Key') }}</span>
    </div>
    <div class="alert-info-item">
      <span class="alert-info-label">* :</span>
      <span class="alert-info-value">{{ t('提取所有key') }}</span>
    </div>
  </BkAlert>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>

<style lang="less">
  .key-opration-alert-info {
    &.bk-alert {
      :deep(.bk-alert-icon-info) {
        align-self: flex-start;
      }
    }

    .alert-info-item {
      display: flex;
      padding-bottom: 4px;
      font-size: @font-size-mini;

      &:last-child {
        padding-bottom: 0;
      }
    }

    .alert-info-label {
      width: 240px;
      padding-right: 8px;
      text-align: right;
      flex-shrink: 0;
    }

    .alert-info-value {
      word-break: break-all;
    }
  }
</style>
