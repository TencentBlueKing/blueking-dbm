<template>
  <bk-resize-layout
    class="webconsole-useing-help"
    style="height: 100%"
    initialDivide="50%"
    :max="900"
    :min="400"
    placement="right"
    immediate
  >
    <template #aside>
      <div class="aside-main">
        <div style="font-weight: 700">{{ t('使用帮助') }}</div>
        <div>1. {{ t('除use dbname外，必须有结束符; 或', { n: '/\G'}) }};</div>
        <div>2. {{ t('结束符后不允许有空白外的字符') }};</div>
        <div>3. {{ t('不允许访问系统库，如', { n: 'mysql information_schema performance_schema db_infobase'}) }};</div>
        <div>4. {{ t('只能输入select，不支持insert, delete, update，且select必须带limit控制行数，行数<=100') }};</div>
        <div>5. {{ t('查询结果数据量不能大于64M') }};</div>
        <div>## Support Statements</div>
        <div>- use dbname</div>
        <div>- select databases();</div>
        <div>- set names utf8;</div>
        <div>- show variables like '%xxx%';</div>
        <div>- show [full] databases|tables [like '%xxx%'];</div>
        <div>- show create table|database name;</div>
        <div>- select * from [db.]table [where cond] [order by ...] limit [skip,]N; (N<=100)</div>
        <div>- select * from [db.]table,[db.]table2 [where cond] [order by ...] limit [skip,]N</div>
      </div>
    </template>
    <template #main>
      <div @click="handleClickMain" class="empty-main"></div>
    </template>
  </bk-resize-layout>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'hide'): void
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleClickMain = () => {
    emits('hide')
  }
</script>
<style lang="less">
  .webconsole-useing-help {
    border: none;

    .bk-resize-layout-aside {
      border: none;
    }

    .aside-main {
      width: 100%;
      height: 100%;
      background: #282829;
      border: 2px solid transparent;
      color: #C4C6CC;
      font-size: 12px;
      line-height: 23px;
      padding: 16px;
      box-sizing: border-box;

      &:hover {
        border-color: blue;
      }
    }

    .empty-main {
      width: 100%;
      height: 100%;
    }
  }
</style>