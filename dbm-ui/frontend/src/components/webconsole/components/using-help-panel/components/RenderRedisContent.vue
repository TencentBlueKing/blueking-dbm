<template>
  <div style="font-weight: bold">## {{ t('使用帮助') }}</div>
  <div>1. {{ t('只支持读取类的指令') }};</div>
  <div>2. {{ t('get、mget指令，返回的value需小于1M') }};</div>
  <div>3. {{ t('复合类型，返回member需小于1000') }};</div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
