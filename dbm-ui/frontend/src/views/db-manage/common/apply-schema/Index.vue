<template>
  <DbFormItem
    :label="t('部署方案选择')"
    required>
    <BkRadioGroup
      v-model="modelValue"
      style="width: 314px">
      <BkRadioButton
        :label="APPLY_SCHEME.AUTO"
        style="flex: 1">
        {{ t('自动推荐方案') }}
        <BkTag
          size="small"
          theme="success">
          {{ t('实验') }}
        </BkTag>
      </BkRadioButton>
      <BkRadioButton
        :label="APPLY_SCHEME.CUSTOM"
        style="flex: 1">
        {{ t('自定义方案') }}
      </BkRadioButton>
    </BkRadioGroup>
  </DbFormItem>
</template>

<script lang="ts">
  export enum APPLY_SCHEME {
    AUTO = 'auto',
    CUSTOM = 'custom',
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<APPLY_SCHEME>({
    required: true,
  });
</script>
