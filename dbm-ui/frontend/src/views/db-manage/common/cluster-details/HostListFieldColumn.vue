<template>
  <BkTableColumn
    field="ip"
    label="IP" />
  <BkTableColumn
    field="host_info.alive"
    :label="t('Agent 状态')">
    <template #default="{ data }: { data: IData }">
      <HostAgentStatus :data="data?.host_info?.alive || 0" />
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="role"
    :title="t('部署角色')">
    <template #default="{ data }: { data: IData }">
      <RenderClusterRole :data="[data.instance_role]" />
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="host_info.bk_idc_city_name"
    :label="t('地域')">
    <template #default="{ data }: { data: IData }">
      {{ data.host_info.bk_idc_city_name || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="bk_sub_zone"
    :label="t('园区')">
    <template #default="{ data }: { data: IData }">
      {{ data.bk_sub_zone || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="bk_os_name"
    :label="t('操作系统')">
    <template #default="{ data }: { data: IData }">
      {{ data.bk_os_name || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="bk_svr_device_cls_name"
    :label="t('机型')">
    <template #default="{ data }: { data: IData }">
      {{ data.bk_svr_device_cls_name || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="host_info.bk_cpu_architecture"
    :label="t('CPU_核_')">
    <template #default="{ data }: { data: IData }">
      {{ data.host_info.bk_cpu || '--' }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="host_info.bk_mem"
    :label="t('内存G')">
    <template #default="{ data }: { data: IData }">
      {{ transformMToG(data.host_info.bk_mem) }}
    </template>
  </BkTableColumn>
  <BkTableColumn
    field="host_info.bk_disk"
    :label="t('磁盘G')">
    <template #default="{ data }: { data: IData }">
      {{ data.host_info.bk_disk || '--' }}
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';
  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  type IData = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number];

  const { t } = useI18n();

  const transformMToG = (value: number) => {
    return value ? (value / 1024).toFixed(2) : '--';
  };
</script>
