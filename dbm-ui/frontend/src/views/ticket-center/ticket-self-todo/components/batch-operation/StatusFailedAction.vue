<template>
  <BkRadioGroup
    v-model="modelValue"
    style="display: block">
    <BkRadio
      label="TERMINATE"
      style="margin-left: 0">
      <BkTag
        size="small"
        theme="danger"
        type="stroke">
        {{ t('终止单据') }}
      </BkTag>
      <span class="ml-4">{{ t('终止后，单据将作废处理') }}</span>
    </BkRadio>
  </BkRadioGroup>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  setTimeout(() => {
    modelValue.value = 'TERMINATE';
  });
</script>
