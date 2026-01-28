<template>
  <div class="machine-selector-table">
    <DbQuickSearch
      v-model="quickSearchValue"
      class="mt-16 mb-16"
      :data="quickSearchData"
      :placeholder="t('请输入或选择条件搜索')"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="machineTable"
      class="db-machine-table"
      :container-height="containerHeight"
      :data-source="realDataSource"
      :disable-select-method="disableSelectMethod"
      :filter-value="quickSearchValue"
      row-key="ip"
      :select-single="single"
      selectable
      :selected="selected"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <TableColumn
        col-key="ip"
        fixed="left"
        :title="t('IP')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          {{ row.ip || '--' }}
        </template>
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
        :filter="columnFilter['instance_role']"
        :title="t('部署角色')"
        width="150">
        <template #default="{ row }: { row: IRowData }">
          <RenderClusterRole :data="[row.instance_role]" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="related_instances"
        :title="t('关联实例')"
        width="200">
        <template #default="{ row }: { row: IRowData }">
          <RelatedInstances :data="row.related_instances" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="related_clusters"
        :min-width="300"
        :title="t('关联集群')">
        <template #default="{ row }: { row: IRowData }">
          <div
            v-for="item in row.related_clusters"
            :key="item.id">
            {{ item.immute_domain }}
          </div>
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_city_id"
        :filter="columnFilter['bk_city_id']"
        :title="t('地域')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.host_info.bk_idc_city_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_sub_zone"
        :filter="columnFilter['bk_sub_zone']"
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
        :filter="columnFilter['bk_os_name']"
        :title="t('操作系统')"
        :width="150">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_os_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="spec_id"
        :filter="columnFilter['spec_id']"
        :title="t('绑定规格')"
        :width="150">
        <template #default="{ row }: { row: IRowData }">
          <SpecDetailPopover
            v-if="row.spec_name"
            :data="row.spec_config">
            <span style="padding-bottom: 2px; border-bottom: 1px dashed #979ba5">{{ row.spec_name }}</span>
          </SpecDetailPopover>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_svr_device_cls_name"
        :filter="columnFilter['bk_svr_device_cls_name']"
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
    </DbTable>
  </div>
</template>

<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import { useHostColumnFilter, useHostQuickSearch } from '@hooks';

  import DbTable from '@components/db-table/IndexNew.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';
  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import type { ISupportClusterType, MachineModel } from '../../types';

  import RelatedInstances from './components/RelatedInstances.vue';

  export interface Props<C extends ISupportClusterType> {
    clusterType: ISupportClusterType;
    dataSourceMap?: {
      [key in C]?: ReturnType<typeof useClusterMachineList<key>>;
    };
    disableSelectMethod?: (data: MachineModel<C>) => boolean | string;
    selected: MachineModel<C>[];
    single?: boolean;
  }

  type Emits = (e: 'selection', list: IRowData[]) => void;

  type IRowData = MachineModel<T>;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const requestHandler = useClusterMachineList(props.clusterType);

  const { quickSearchData, quickSearchValue } = useHostQuickSearch(props.clusterType, {
    serviceHandler: () => {
      fetchData();
    },
  });
  const columnFilter = useHostColumnFilter(props.clusterType);

  const instanceTableRef = useTemplateRef('machineTable');

  const containerHeight = 570 - 32 - 16; // 去除搜索框的高度和margin bottom

  const realDataSource = (params: any) => (props.dataSourceMap?.[props.clusterType as T] || requestHandler)(params);

  const fetchData = () => {
    instanceTableRef.value!.fetchData(Object.assign({}, quickSearchValue.value));
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  const handleSelection = (_key: string[], list: IRowData[]) => {
    emits('selection', list);
  };

  const transformMToG = (value: number) => {
    return value ? (value / 1024).toFixed(2) : '--';
  };

  onMounted(() => {
    fetchData();
  });
</script>

<style lang="less">
  .machine-selector-table {
    height: 570px;
    padding: 0 24px;
  }
</style>
