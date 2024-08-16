<template>
  <div style="font-weight: bold">## {{ t('使用帮助') }}</div>
  <div>1. {{ t('支持 show databases、show tables from db1 等部分 show 语句') }};</div>
  <div>2. {{ t('只能输入select，不支持 insert, delete, update，且 select 必须带limit控制行数，行数<=1000') }};</div>
  <div>3. {{ t('暂时不支持 use 语句') }};</div>
  <div>4. {{ t('不允许访问系统库，如 mysql information_schema performance_schema db_infobase') }};</div>
  <div>5. {{ t('查询结果数据量不能大于64M') }};</div>
  <div style="font-weight: bold">## {{ t('示例') }}</div>
  <div>- show databases;</div>
  <div>- show tables from db1;</div>
  <div>- select * from [db.]table [where cond] [order by ...] limit [skip,]N; (N&lt;=1000)</div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
</script>
