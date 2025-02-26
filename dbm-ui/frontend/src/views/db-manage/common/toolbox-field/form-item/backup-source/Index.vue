<template>
  <BkFormItem
    :label="t('备份源')"
    property="backupSource"
    required>
    <BkRadioGroup v-model="modelValue">
      <BkRadio :label="BackupSourceType.LOCAL">
        {{ t('本地备份') }}
      </BkRadio>
      <BkRadio :label="BackupSourceType.REMOTE">
        {{ t('远程备份') }}
      </BkRadio>
    </BkRadioGroup>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { BackupSourceType } from '@services/types';

  const modelValue = defineModel<BackupSourceType>({
    default: BackupSourceType.LOCAL,
    required: true,
  });

  const { t } = useI18n();
</script>
