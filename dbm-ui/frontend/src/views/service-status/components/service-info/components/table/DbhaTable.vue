<template>
  <BkTable :data="list">
    <BkTableColumn
      fixed="left"
      :label="t('实例')"
      :width="200">
      <template #default="{ data }: { data: DbhaServiceStatusModel }">
        <span>{{ data.ip }}</span>
        <span v-if="data.port">:{{ data.port }}</span>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('状态')"
      :width="100">
      <template #default="{ data }: { data: DbhaServiceStatusModel }">
        <DbStatus :theme="data.statusInfo.theme">{{ data.statusInfo.text }}</DbStatus>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="module"
      :label="t('类型')">
    </BkTableColumn>
    <BkTableColumn
      field="db_type"
      :label="t('探测组件类型')">
    </BkTableColumn>
    <BkTableColumn
      field="bk_city_name"
      :label="t('城市名')">
    </BkTableColumn>
    <BkTableColumn
      field="startTimeDisplay"
      :label="t('启动时间')">
    </BkTableColumn>
    <BkTableColumn
      field="lastTimeDisplay"
      :label="t('上次更新时间')">
    </BkTableColumn>
    <BkTableColumn
      field="report_interval"
      :label="t('上报间隔')">
      <template #default="{ data }: { data: DbhaServiceStatusModel }">
        {{ data.report_interval || '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DbhaServiceStatusModel from '@services/model/db-extension/dbha-service-status';

  interface Props {
    list: DbhaServiceStatusModel[];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
