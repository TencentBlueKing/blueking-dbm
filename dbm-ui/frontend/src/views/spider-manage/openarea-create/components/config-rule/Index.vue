<template>
  <div>
    <DbTable :columns="tableColumns" />
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const tableColumns = [
    {
      label: t('克隆 DB'),
    },
    {
      label: t('克隆表结构'),
    },
    {
      label: t('克隆表数据'),
    },
    {
      label: t('生成目标 DB 范式'),
    },
    {
      label: t('初始化授权'),
    },
    {
      label: t('操作'),
      width: 120,
    },
  ];
</script>
<style lang="postcss">
  .root {
    display: block
  }
</style>
