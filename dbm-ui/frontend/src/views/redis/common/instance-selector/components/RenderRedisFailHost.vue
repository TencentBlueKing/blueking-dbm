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
  <div class="instance-selector-render-topo-host">
    <BkInput
      v-model="search"
      clearable
      :placeholder="$t('请输入 IP 进行搜索')"
      @clear="handlePageValueChange(1)"
      @enter="handleClickSearch" />
    <BkLoading
      :loading="isTableDataLoading"
      :z-index="2">
      <DbOriginalTable
        :columns="columns"
        :data="tableData"
        :is-anomalies="isAnomalies"
        :is-searching="!!search"
        :max-height="530"
        :pagination="pagination.count < 10 ? false : pagination"
        remote-pagination
        :settings="tableSettings"
        style="margin-top: 12px;"
        @clear-search="handleClearSearch"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange"
        @refresh="fetchData"
        @row-click.stop="handleRowClick" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisHostModel from '@services/model/redis/redis-host';
  // TODO INTERFACE
  import {
    queryClusterHostList,
    queryMasterSlavePairs,
  } from '@services/source/redisToolbox';

  import { ipv4 } from '@common/regex';

  import DbStatus from '@components/db-status/index.vue';

  import type { InstanceSelectorValues } from '../Index.vue';

  import { activePanelInjectionKey } from './PanelTab.vue';

  import type { TableProps } from '@/types/bkui-vue';

  interface TableItem {
    data: RedisHostModel
  }

  export interface Props {
    node?: {
      id: number,
      name: string
      clusterDomain: string
    },
    role?: string
    tableSettings: TableProps['settings'],
    lastValues: InstanceSelectorValues,
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  export  interface ChoosedFailedMasterItem {
    cluster_id: number;
    ip: string;
    role?: string;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();


  const { t } = useI18n();
  const activePanel = inject(activePanelInjectionKey) ?? ref('idleHosts');

  const search = ref('');
  const isAnomalies = ref(false);

  const checkedMap = shallowRef<Record<string, ChoosedFailedMasterItem>>({});

  const masterSlaveMap: {[key: string]: string} = {};

  watch(() => props.lastValues, (lastValues) => {
    // 切换 tab 回显选中状态 \ 预览结果操作选中状态
    checkedMap.value = {};
    const checkedList = lastValues.masterFailHosts;
    for (const item of checkedList) {
      checkedMap.value[item.ip] = item;
    }
  }, { immediate: true, deep: true });

  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });
  const isTableDataLoading = ref(false);
  const tableData = shallowRef<RedisHostModel []>([]);
  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item.ip]).length
  ));
  const isIndeterminate = computed(() => !isSelectedAll.value && Object.values(checkedMap.value).length > 0);

  const columns = [
    {
      width: 60,
      fixed: 'left',
      label: () => (
        <bk-checkbox
          indeterminate={isIndeterminate.value}
          model-value={isSelectedAll.value}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={handleSelectPageAll}
        />
      ),
      render: ({ data }: {data: RedisHostModel}) => (
        <bk-checkbox
          style="vertical-align: middle;"
          model-value={Boolean(checkedMap.value[data.ip])}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={(value: boolean) => handleTableSelectOne(value, data)}
        />
      ),
    },
    {
      fixed: 'left',
      minWidth: 160,
      label: props.role ? props.role.charAt(0).toUpperCase() + props.role.slice(1) : t('实例'),
      field: 'ip',
    },
    {
      label: t('角色'),
      field: 'role',
      showOverflowTooltip: true,
      filter: {
        list: [{ text: 'master', value: 'master' }, { text: 'slave', value: 'slave' }, { text: 'proxy', value: 'proxy' }],
      },
    },
    {
      label: t('实例状态'),
      field: 'status',
      render: ({ data } : TableItem) => {
        const info = !data.isMasterFailover ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      minWidth: 100,
      label: t('管控区域'),
      field: 'cloud_area',
      render: ({ data } : TableItem) => data.host_info?.cloud_area.name || '--',
    },
    {
      minWidth: 100,
      label: t('Agent状态'),
      field: 'alive',
      sort: true,
      render: ({ data } : TableItem) => {
        const info = data.host_info?.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('主机名称'),
      field: 'host_name',
      showOverflowTooltip: true,
      render: ({ data } : TableItem) => data.host_info?.host_name || '--',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
      showOverflowTooltip: true,
      render: ({ data } : TableItem) => data.host_info?.os_name || '--',
    },
    {
      label: t('所属云厂商'),
      field: 'cloud_vendor',
      showOverflowTooltip: true,
      render: ({ data }: TableItem) => data.host_info?.cloud_vendor || '--',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
      showOverflowTooltip: true,
      render: ({ data }: TableItem) => data.host_info?.os_type || '--',
    },
    {
      label: t('主机ID'),
      field: 'host_id',
      showOverflowTooltip: true,
      render: ({ data } : TableItem) => data.host_info?.host_id || '--',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
      showOverflowTooltip: true,
      render: ({ data } : TableItem) => data.host_info?.agent_id || '--',
    },
  ];

  const fetchData = () => {
    if (props.node) {
      isTableDataLoading.value = true;
      queryClusterHostList({
        cluster_id: props.node.id,
      })
        .then((data) => {
          // 取消限制
          // tableData.value = data.filter(item => item.isMasterFailover);
          const arr = data.filter(item => item.isMaster);
          tableData.value = arr;
          pagination.count = arr.length;
          isAnomalies.value = false;
        })
        .catch(() => {
          isAnomalies.value = true;
        })
        .finally(() => {
          isTableDataLoading.value = false;
        });
      queryMasterSlavePairs({
        cluster_id: props.node.id,
      }).then((data) => {
        data.forEach(item => masterSlaveMap[item.master_ip] = item.slave_ip);
      })
        .catch((e) => {
          console.error('queryMasterSlavePairs error: ', e);
        });
    }
  };

  watch(() => props.node, () => {
    if (props.node) {
      fetchData();
    }
  });

  const triggerChange = () => {
    const result = Object.values(checkedMap.value);
    if (activePanel?.value) {
      emits('change', {
        ...props.lastValues,
        [activePanel.value]: result,
      });
    }
  };

  const formatValue = (data: RedisHostModel) => ({
    cluster_id: data.cluster_id,
    ip: data.ip || '',
  });

  const handleSelectPageAll = (checked: boolean) => {
    const lastCheckMap = { ...checkedMap.value };
    for (const item of tableData.value) {
      if (checked) {
        lastCheckMap[item.ip] = formatValue(item);
      } else {
        delete lastCheckMap[item.ip];
      }
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleTableSelectOne = (checked: boolean, data: RedisHostModel) => {
    const lastCheckMap = { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.ip] = formatValue(data);
    } else {
      delete lastCheckMap[data.ip];
    }
    checkedMap.value = lastCheckMap;
    triggerChange();
  };

  const handleRowClick = (key: number, data: RedisHostModel) => {
    const checked = checkedMap.value[data.ip];
    handleTableSelectOne(!checked, data);
  };

  const handleClickSearch = () => {
    if (!search.value) {
      handleClearSearch();
      return;
    }
    if (!ipv4.test(_.trim(search.value))) {
      return;
    }
    if (props.node) {
      handlePageValueChange(1);
      queryClusterHostList({
        cluster_id: props.node.id,
        ip: search.value,
      })
        .then((data) => {
          tableData.value = data;
          pagination.count = data.length;
          isAnomalies.value = false;
        })
        .catch(() => {
          isAnomalies.value = true;
        })
        .finally(() => {
          isTableDataLoading.value = false;
        });
    }
  };

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
  };
  // 切换页码
  const handlePageValueChange = (pageValue:number) => {
    pagination.current = pageValue;
  };
  // 清空搜索
  const handleClearSearch = () => {
    search.value = '';
    handlePageValueChange(1);
  };
</script>

<style lang="less">
  .instance-selector-render-topo-host {
    padding: 0 24px;

    .bk-table-body {
      tr {
        cursor: pointer;
      }
    }
  }
</style>
