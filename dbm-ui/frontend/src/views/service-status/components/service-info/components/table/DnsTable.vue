<template>
  <BkTable :data="list">
    <BkTableColumn
      field="ip"
      fixed="left"
      label="IP"
      :width="200">
    </BkTableColumn>
    <BkTableColumn
      :label="t('状态')"
      :width="100">
      <template #default="{ data }: { data: DnsServiceStatusModel }">
        <DbStatus :theme="data.statusInfo.theme">{{ data.statusInfo.text }}</DbStatus>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="bk_city"
      :label="t('城市名')">
    </BkTableColumn>
    <BkTableColumn
      field="isAccessDisplay"
      :label="t('可访问')">
    </BkTableColumn>
    <BkTableColumn
      field="updater"
      :label="t('更新人')">
    </BkTableColumn>
    <BkTableColumn
      field="updateAtDisplay"
      :label="t('更新时间')">
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DnsServiceStatusModel from '@services/model/db-extension/dns-service-status';

  interface Props {
    list: DnsServiceStatusModel[];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
