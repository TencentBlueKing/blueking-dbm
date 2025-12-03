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
      <template #default="{ data }: { data: DrsServiceStatusModel }">
        <ClusterInstanceStatus :data="data.status" />
      </template>
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

  import DrsServiceStatusModel from '@services/model/db-extension/drs-service-status';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  interface Props {
    list: DrsServiceStatusModel[];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
