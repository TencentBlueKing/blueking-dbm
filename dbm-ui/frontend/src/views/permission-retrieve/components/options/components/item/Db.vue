<template>
  <BkFormItem
    :label="t('访问 DB')"
    property="dbs">
    <BkTagInput
      v-model="modelValue"
      allow-auto-match
      allow-create
      collapse-tags
      has-delete-icon
      :placeholder="t('请输入DB，支持%')" />
  </BkFormItem>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<string[]>({
    required: true,
  });
</script>
