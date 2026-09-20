<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="host-selector-table">
    <DbQuickSearch
      v-model="quickSearchValue"
      class="mt-16 mb-16"
      :data="quickSearchData"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="hostTable"
      class="db-host-table"
      :container-height="containerHeight"
      :data-source="realDataSource"
      :disable-select-method="disableSelectMethod"
      :filter-value="quickSearchValue"
      row-click-selectable
      row-key="ip"
      :select-single="single"
      selectable
      :selected="selected"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <TableColumn
        col-key="ip"
        :filter="tableFilter.ip"
        fixed="left"
        :min-width="140"
        :title="t('主机IP')">
      </TableColumn>
      <TableColumn
        col-key="host_info.alive"
        :title="t('Agent状态')"
        width="96">
        <template #default="{ row }: { row: IRowData }">
          <HostAgentStatus :data="row?.host_info?.alive || 0" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="instance_role"
        :filter="tableFilter.instance_role"
        :min-width="140"
        :title="t('部署角色')">
        <template #default="{ row }: { row: IRowData }">
          <RenderClusterRole :data="[row.instance_role]" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="related_instances"
        :min-width="200"
        :title="t('关联实例')">
        <template #default="{ row }: { row: IRowData }">
          <RenderInstance
            v-if="row.related_instances?.length"
            :data="row.related_instances" />
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="related_clusters"
        :min-width="200"
        :title="t('所属集群')">
        <template #default="{ row }: { row: IRowData }">
          <RenderCluster
            v-if="row.related_clusters?.length"
            :data="row.related_clusters" />
          <span v-else>--</span>
        </template>
      </TableColumn>
      <!-- 仅 Redis 主机展示架构类型列（同类型多架构） -->
      <TableColumn
        v-if="clusterType === ClusterTypes.REDIS"
        col-key="cluster_type_name"
        :min-width="120"
        :title="t('架构类型')" />
      <TableColumn
        col-key="bk_city_id"
        :filter="tableFilter.bk_city_id"
        :title="t('地域')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          {{ row.host_info?.bk_idc_city_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_sub_zone"
        :filter="tableFilter.bk_sub_zone"
        :title="t('园区')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_sub_zone || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_rack_id"
        :title="t('机架ID')"
        :width="100">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_rack_id || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_os_name"
        :filter="tableFilter.bk_os_name"
        :title="t('操作系统')"
        :width="150">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_os_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="spec_id"
        :filter="tableFilter.spec_id"
        :title="t('绑定规格')"
        :width="160">
        <template #default="{ row }: { row: IRowData }">
          <SpecDetailPopover
            v-if="row.spec_name"
            :data="row.spec_config">
            <span class="host-list-spec-name">
              <span :class="{ 'host-list-spec-disabled': !row.spec_enable }">{{ row.spec_name }}</span>
              <DbTag
                v-if="!row.spec_enable"
                class="ml-4"
                size="small">
                {{ t('已停用') }}
              </DbTag>
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
        :filter="tableFilter.bk_svr_device_cls_name"
        :title="t('机型')"
        :width="120">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_svr_device_cls_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="host_info.bk_cpu_architecture"
        :title="t('CPU（核）')"
        :width="100">
        <template #default="{ row }: { row: IRowData }">
          {{ row.host_info?.bk_cpu || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="host_info.bk_mem"
        :title="t('内存（G）')"
        :width="100">
        <template #default="{ row }: { row: IRowData }">
          {{ transformMToG(row.host_info?.bk_mem) }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="host_info.bk_disk"
        :title="t('磁盘（G）')"
        :width="100">
        <template #default="{ row }: { row: IRowData }">
          {{ row.host_info?.bk_disk || '--' }}
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts" generic="T extends ISupportHostType">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { queryBizMachineAttrs } from '@services/source/dbbase';

  import { ClusterTypes, specialOptionLabelMap, SpecialOptions } from '@common/const';
  import { batchSplitRegex, ipPort, ipv4 } from '@common/regex';

  import MultipleInput from '@components/db-table/components/MultipleInput.vue';
  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import SpecDetailPopover from '@components/spec-detail-popover/Index.vue';

  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';

  import { hostMachineDataSourceMap } from '../dataSource';
  import { type HostModel, type ISupportHostType } from '../types';

  import RenderCluster from './render-cluster/Index.vue';
  import RenderInstance from './render-instance/Index.vue';

  export interface Props<C extends ISupportHostType> {
    clusterType: ISupportHostType;
    dataSourceMap?: {
      [key in C]?: (params: any) => Promise<any>;
    };
    disableSelectMethod?: (data: HostModel<C>) => boolean | string;
    selected: HostModel<C>[];
    single?: boolean;
  }

  type Emits = (e: 'selection', list: IRowData[]) => void;

  type IRowData = HostModel<T>;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const hostTableRef = useTemplateRef('hostTable');

  const containerHeight = 570 - 32 - 16; // 去除搜索框的高度和margin bottom

  // 搜索字段对齐集群详情页主机列表
  const machineAttrs = [
    'bk_city_id',
    'bk_sub_zone',
    'bk_os_name',
    'spec_id',
    'instance_role',
    'bk_svr_device_cls_name',
  ] as const;

  // 这些属性存在空值，空值统一归为「未知」选项
  const emptyValueAttrs = ['bk_city_id', 'bk_os_name', 'bk_sub_zone', 'bk_svr_device_cls_name'];

  const getBizMachineAttrs = (attr: (typeof machineAttrs)[number]) =>
    queryBizMachineAttrs({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_type: props.clusterType,
      machine_attrs: machineAttrs.join(','),
    }).then((data) => {
      const formatList = data[attr].map((item) => ({
        label: attr === 'spec_id' ? `${item.text} [${item.value}]` : item.text,
        value: item.value,
      }));

      if (emptyValueAttrs.includes(attr)) {
        const filterList = formatList.filter((item) => item.value !== null && item.value !== '');
        if (filterList.length !== formatList.length) {
          return filterList.concat({
            label: specialOptionLabelMap[SpecialOptions.EMPTY],
            value: SpecialOptions.EMPTY,
          });
        }
        return filterList;
      }

      return formatList;
    });

  const quickSearchData = [
    {
      id: 'ip',
      name: 'IP',
      type: 'multiple-input' as const,
      validator: (value: string) => {
        if (value.split(batchSplitRegex).some((item) => !ipv4.test(item))) {
          return t('格式错误');
        }
        return true;
      },
    },
    {
      id: 'domain',
      name: t('所属集群'),
      type: 'multiple-input' as const,
      validator: (value: string) => {
        return !ipPort.test(value) && !ipv4.test(value);
      },
    },
    {
      id: 'instance_role',
      name: t('部署角色'),
      remoteMethod: () => getBizMachineAttrs('instance_role'),
      type: 'multiple' as const,
    },
    {
      id: 'bk_city_id',
      name: t('地域'),
      remoteMethod: () => getBizMachineAttrs('bk_city_id'),
      type: 'multiple' as const,
    },
    {
      id: 'bk_sub_zone',
      name: t('园区'),
      remoteMethod: () => getBizMachineAttrs('bk_sub_zone'),
      type: 'multiple' as const,
    },
    {
      id: 'bk_os_name',
      name: t('操作系统'),
      remoteMethod: () => getBizMachineAttrs('bk_os_name'),
      type: 'multiple' as const,
    },
    {
      id: 'spec_id',
      name: t('绑定规格'),
      remoteMethod: () => getBizMachineAttrs('spec_id'),
      type: 'multiple' as const,
    },
    {
      id: 'bk_svr_device_cls_name',
      name: t('机型'),
      remoteMethod: () => getBizMachineAttrs('bk_svr_device_cls_name'),
      type: 'multiple' as const,
    },
  ];

  // 表头筛选与搜索栏是同一套条件的两个入口，字段 id 与搜索项、列 col-key 保持一致
  const tableFilter = {
    bk_city_id: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_city_id'),
      },
      showConfirmAndReset: true,
    },
    bk_os_name: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_os_name'),
      },
      showConfirmAndReset: true,
    },
    bk_sub_zone: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_sub_zone'),
      },
      showConfirmAndReset: true,
    },
    bk_svr_device_cls_name: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('bk_svr_device_cls_name'),
      },
      showConfirmAndReset: true,
    },
    instance_role: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('instance_role'),
      },
      showConfirmAndReset: true,
    },
    ip: {
      component: markRaw(MultipleInput),
      showConfirmAndReset: true,
    },
    spec_id: {
      component: markRaw(MultipleSelect),
      props: {
        remoteMethod: () => getBizMachineAttrs('spec_id'),
      },
      showConfirmAndReset: true,
    },
  };

  const quickSearchValue = ref<Record<string, any>>({});

  // 默认数据源：按主机类型映射 machine list 接口；调用方可通过 dataSourceMap 按类型覆盖（含角色过滤）
  const realDataSource = (params: any) => {
    if (props.dataSourceMap?.[props.clusterType as T]) {
      return props.dataSourceMap[props.clusterType as T]!(params);
    }
    return hostMachineDataSourceMap[props.clusterType](params);
  };

  const fetchData = () => {
    hostTableRef.value!.fetchData(Object.assign({}, quickSearchValue.value));
  };

  // DbQuickSearch 挂载时会回显一次并 emit change，首次列表数据由此拉取，不再额外 onMounted 请求
  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string | string[]>) => {
    // 搜索栏与筛选面板都按逗号分隔字符串取值，多选列重置时表格会回传数组，入口处统一归一
    quickSearchValue.value = _.mapValues(filterValue, (value) => (Array.isArray(value) ? value.join(',') : value));
    fetchData();
  };

  const handleSelection = (_key: string[], list: IRowData[]) => {
    emits('selection', list);
  };

  const transformMToG = (value?: number) => (value ? (value / 1024).toFixed(2) : '--');
</script>

<style lang="less">
  .host-selector-table {
    height: 570px;
    padding: 0 24px;

    .host-list-spec-name {
      padding-bottom: 2px;
      border-bottom: 1px dashed #979ba5;
    }

    .host-list-spec-disabled {
      color: #c4c6cc;
      text-decoration: line-through #c4c6cc;
    }

    .host-list-spec-unbound {
      color: #ea3636;
    }
  }
</style>
