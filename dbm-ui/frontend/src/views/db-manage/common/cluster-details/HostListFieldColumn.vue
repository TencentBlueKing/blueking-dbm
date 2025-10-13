<template>
  <TableColumn
    col-key="ip"
    :filter="tableFilter['ip']"
    fixed="left"
    title="IP"
    width="150">
  </TableColumn>
  <TableColumn
    col-key="host_info.alive"
    :title="t('Agent 状态')"
    width="96">
    <template #default="{ row }: { row: IRowData }">
      <HostAgentStatus :data="row?.host_info?.alive || 0" />
    </template>
  </TableColumn>
  <TableColumn
    col-key="instance_role"
    :filter="tableFilter['instance_role']"
    :title="t('部署角色')"
    width="150">
    <template #default="{ row }: { row: IRowData }">
      <RenderClusterRole :data="[row.instance_role]" />
    </template>
  </TableColumn>
  <TableColumn
    col-key="host_info.bk_idc_city_name"
    :filter="tableFilter['region']"
    :title="t('地域')">
    <template #default="{ row }: { row: IRowData }">
      {{ row.host_info.bk_idc_city_name || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="bk_sub_zone"
    :filter="tableFilter['bk_sub_zone']"
    :title="t('园区')">
    <template #default="{ row }: { row: IRowData }">
      {{ row.bk_sub_zone || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="bk_os_name"
    :filter="tableFilter['bk_os_name']"
    :title="t('操作系统')"
    :width="150">
    <template #default="{ row }: { row: IRowData }">
      {{ row.bk_os_name || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="spec_ids"
    :filter="tableFilter['spec_ids']"
    :title="t('绑定规格')"
    :width="150">
    <template #default="{ row }: { row: IRowData }">
      <SpecDetailPopover
        v-if="row.spec_name"
        :data="row.spec_config">
        {{ row.spec_name }}
      </SpecDetailPopover>
      <span v-else>--</span>
    </template>
  </TableColumn>
  <TableColumn
    col-key="bk_svr_device_cls_name"
    :filter="tableFilter['bk_svr_device_cls_name']"
    :title="t('机型')">
    <template #default="{ row }: { row: IRowData }">
      {{ row.bk_svr_device_cls_name || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="host_info.bk_cpu_architecture"
    :title="t('CPU_核_')"
    :width="100">
    <template #default="{ row }: { row: IRowData }">
      {{ row.host_info.bk_cpu || '--' }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="host_info.bk_mem"
    :title="t('内存G')">
    <template #default="{ row }: { row: IRowData }">
      {{ transformMToG(row.host_info.bk_mem) }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="host_info.bk_disk"
    :title="t('磁盘G')">
    <template #default="{ row }: { row: IRowData }">
      {{ row.host_info.bk_disk || '--' }}
    </template>
  </TableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { DBTypes } from '@common/const';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';
  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { useTableFilter } from './hooks';

  type IRowData = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number];

  interface Props {
    dbType: DBTypes;
    // eslint-disable-next-line vue/no-unused-properties
    roleList: {
      label: string;
      value: string;
    }[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableFilter = useTableFilter(props.dbType, {
    roleList: toRef(props, 'roleList'),
  });

  const transformMToG = (value: number) => {
    return value ? (value / 1024).toFixed(2) : '--';
  };
</script>
