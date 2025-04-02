<template>
  <div style="font-weight: bold">## {{ t('使用帮助') }}</div>
  <div>1. {{ t('只支持查询类操作') }};</div>
  <div>2. {{ t('查询结果数据量上限为64M') }};</div>
  <div>3. {{ t('查询任务时间不能超过5分钟') }};</div>
  <div>4. {{ t('不允许访问系统库，如admin config') }};</div>
  <div style="font-weight: bold">## {{ t('示例') }}</div>
  <div>- db.isMaster()rs.slave0k();</div>
  <div>- show dbs;</div>
  <div>- use dbname;</div>
  <div>- db;</div>
  <div>- db.stats();</div>
  <div>- show tables;</div>
  <div>- db.col.findlfindone([cond..]);</div>
  <div>- db.col.stats();</div>
  <div>- db.col.getIndexes();</div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
