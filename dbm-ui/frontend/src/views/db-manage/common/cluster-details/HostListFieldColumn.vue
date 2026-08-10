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
    col-key="bk_city_id"
    :filter="tableFilter['bk_city_id']"
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
    col-key="bk_rack_id"
    :title="t('机架 ID')">
    <template #default="{ row }: { row: IRowData }">
      {{ row.bk_rack_id || '--' }}
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
    col-key="spec_id"
    :filter="tableFilter['spec_id']"
    :title="t('绑定规格')"
    :width="160">
    <template #default="{ row }: { row: IRowData }">
      <SpecDetailPopover
        v-if="row.spec_name"
        :data="row.spec_config">
        <span class="host-list-spec-name">
          {{ row.spec_name }}
          <span
            v-if="row.enable === false"
            class="host-list-spec-disabled">
            {{ t('已停用') }}
          </span>
        </span>
      </SpecDetailPopover>
      <span
        v-else
        class="host-list-spec-unbound">
        {{ t('未绑定') }}
      </span>
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
    :title="t('内存G')"
    :width="100">
    <template #default="{ row }: { row: IRowData }">
      {{ transformMToG(row.host_info.bk_mem) }}
    </template>
  </TableColumn>
  <TableColumn
    col-key="host_info.bk_disk"
    :title="t('磁盘G')"
    :width="100">
    <template #default="{ row }: { row: IRowData }">
      {{ row.host_info.bk_disk || '--' }}
    </template>
  </TableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { ClusterTypes } from '@common/const';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';
  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { useHostListTableFilter } from './hooks';

  type IRowData = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number];

  interface Props {
    clusterId: number;
    clusterType: ClusterTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableFilter = useHostListTableFilter(props.clusterType, props.clusterId);

  const transformMToG = (value: number) => {
    return value ? (value / 1024).toFixed(2) : '--';
  };
</script>
<style lang="less">
  .host-list-spec-name {
    padding-bottom: 2px;
    border-bottom: 1px dashed #979ba5;
  }

  .host-list-spec-disabled {
    display: inline-block;
    height: 18px;
    padding: 0 4px;
    margin-left: 4px;
    font-size: 12px;
    line-height: 18px;
    color: #979ba5;
    vertical-align: middle;
    background: #f0f1f5;
    border-radius: 2px;
  }

  .host-list-spec-unbound {
    color: #ea3636;
  }
</style>
