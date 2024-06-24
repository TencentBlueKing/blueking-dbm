<template>
  <div>
    <BkAlert
      closable
      theme="info"
      :title="t('数据迁移：数据同步复制到新集群')" />
    <BkInput
      :placeholder="t('请输入集群名称')"
      style="width: 500px; margin-top: 16px" />
    <BkTable
      class="mt-16"
      :columns="tableColumns" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const tableColumns = [
    {
      label: t('源集群'),
    },
    {
      label: t('目标集群'),
    },
    {
      label: t('迁移类型'),
    },
    {
      label: t('迁移 DB'),
    },
    {
      label: t('忽略 DB'),
    },
    {
      label: t('关联单据'),
    },
    {
      label: t('状态'),
    },
    {
      label: t('创建时间'),
    },
    {
      label: t('操作'),
    },
  ];
</script>
