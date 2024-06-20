<template>
  <BkFormItem
    :label="t('字符集')"
    property="charset"
    required>
    <BkSelect
      v-model="modelValue"
      style="width: 360px">
      <BkOption value="default"> default </BkOption>
      <BkOption value="utf8mb4"> utf8mb4 </BkOption>
      <BkOption value="utf8"> utf8 </BkOption>
      <BkOption value="latin1"> latin1 </BkOption>
      <BkOption value="gbk"> gbk </BkOption>
      <BkOption value="gb2312"> gb2312 </BkOption>
    </BkSelect>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<string>({
    required: true,
  });
</script>
