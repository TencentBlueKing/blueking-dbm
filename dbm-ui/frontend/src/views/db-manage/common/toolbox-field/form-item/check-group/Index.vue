<template>
  <BkFormItem class="mb-8">
    <BkCheckbox v-model="isCheckProcess">
      {{ t('检查业务来源的连接') }}
    </BkCheckbox>
  </BkFormItem>
  <BkFormItem class="mb-8">
    <BkCheckbox v-model="isVerifyChecksum">
      {{ t('检查主从同步延迟') }}
    </BkCheckbox>
  </BkFormItem>
  <BkFormItem class="mb-8">
    <BkCheckbox v-model="isCheckDelay">
      {{ t('检查主从数据校验结果') }}
    </BkCheckbox>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const isCheckProcess = defineModel<boolean>('is_check_process', {
    required: true,
  });

  const isVerifyChecksum = defineModel<boolean>('is_verify_checksum', {
    required: true,
  });

  const isCheckDelay = defineModel<boolean>('is_check_delay', {
    required: true,
  });
</script>
