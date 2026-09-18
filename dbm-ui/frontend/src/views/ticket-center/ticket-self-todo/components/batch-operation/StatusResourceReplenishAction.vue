<template>
  <BkRadioGroup
    v-model="modelValue"
    style="display: block">
    <BkRadio
      label="APPROVE"
      style="width: 100%">
      <DbTag
        theme="success"
        type="stroke">
        {{ t('重试') }}
      </DbTag>
      <span class="ml-4">{{ t('重试后，单据将再次尝试申请资源') }}</span>
    </BkRadio>
    <BkRadio
      label="TERMINATE"
      style="margin-left: 0">
      <DbTag
        theme="danger"
        type="stroke">
        {{ t('终止单据') }}
      </DbTag>
      <span class="ml-4">{{ t('终止后，单据将作废处理') }}</span>
    </BkRadio>
  </BkRadioGroup>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const modelValue = defineModel<string>();

  const { t } = useI18n();
</script>
