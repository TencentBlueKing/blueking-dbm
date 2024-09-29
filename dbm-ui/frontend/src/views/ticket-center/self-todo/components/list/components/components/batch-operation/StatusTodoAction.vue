<template>
  <BkRadioGroup
    v-model="modelValue"
    style="display: block">
    <BkRadio
      label="APPROVE"
      style="width: 100%">
      <BkTag
        size="small"
        theme="success"
        type="stroke">
        {{ t('确认执行') }}
      </BkTag>
      <span>{{ t('确认后，单据将进入下一步骤') }}</span>
    </BkRadio>
    <BkRadio
      label="TERMINATE"
      style="margin-left: 0">
      <BkTag
        size="small"
        theme="danger"
        type="stroke">
        {{ t('终止单据') }}
      </BkTag>
      <span>{{ t('终止后，单据将作废处理') }}</span>
    </BkRadio>
  </BkRadioGroup>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<string>();
</script>
