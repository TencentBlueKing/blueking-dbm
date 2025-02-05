<template>
  <BkFormItem class="mb-8">
    <BkCheckbox v-model="modelValue.is_check_process">
      {{ t('检查业务来源的连接') }}
    </BkCheckbox>
  </BkFormItem>
  <BkFormItem class="mb-8">
    <BkCheckbox v-model="modelValue.is_check_delay">
      {{ t('检查主从同步延迟') }}
    </BkCheckbox>
  </BkFormItem>
  <BkFormItem class="mb-8">
    <BkCheckbox v-model="modelValue.is_verify_checksum">
      {{ t('检查主从数据校验结果') }}
    </BkCheckbox>
  </BkFormItem>
</template>
<script lang="ts">
  export const createCheckPayload = () => ({
    is_check_process: false,
    is_check_delay: false,
    is_verify_checksum: false,
  });
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const modelValue = defineModel<ReturnType<typeof createCheckPayload>>({
    required: true,
  });
</script>
