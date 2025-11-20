<template>
  <span>
    <BkRadio
      checked
      label>
      {{ t('随机') }}
    </BkRadio>
  </span>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
