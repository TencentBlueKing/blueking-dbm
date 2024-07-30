<template>
  <BkResizeLayout
    class="webconsole-useing-help"
    initial-divide="50%"
    :max="900"
    :min="400"
    placement="right"
    style="height: 100%"
    :trigger-width="20">
    <template #aside>
      <div class="aside-main">
        <div style="font-weight: 700">## {{ t('使用帮助') }}</div>
        <div>1. {{ t('支持 show databases、show tables from db1 等部分 show 语句') }};</div>
        <div>
          2. {{ t('只能输入select，不支持 insert, delete, update，且 select 必须带limit控制行数，行数<=1000') }};
        </div>
        <div>3. {{ t('暂时不支持 use 语句') }};</div>
        <div>4. {{ t('不允许访问系统库，如 mysql information_schema performance_schema db_infobase') }};</div>
        <div>5. {{ t('查询结果数据量不能大于64M') }};</div>
        <div style="font-weight: 700">## {{ t('示例') }}</div>
        <div>- show databases;</div>
        <div>- show tables from db1;</div>
        <div>- select * from [db.]table [where cond] [order by ...] limit [skip,]N; (N&lt;=1000)</div>
      </div>
    </template>
    <template #main>
      <div
        class="empty-main"
        @click="handleClickMain"></div>
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'hide'): void;
  }

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleClickMain = () => {
    emits('hide');
  };
</script>
<style lang="less">
  .webconsole-useing-help {
    border: none;

    .bk-resize-layout-aside {
      border: none;

      .bk-resize-trigger:hover {
        border-left: 2px solid #3a84ff;
      }
    }

    .aside-main {
      width: 100%;
      height: 100%;
      padding: 16px;
      font-size: 12px;
      line-height: 23px;
      color: #c4c6cc;
      background: #282829;
      border: 2px solid transparent;
      box-sizing: border-box;
    }

    .empty-main {
      width: 100%;
      height: 100%;
    }
  }
</style>
