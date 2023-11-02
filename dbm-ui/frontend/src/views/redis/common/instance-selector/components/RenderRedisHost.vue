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
        class="table-box"
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
  import {  queryClusterHostList, queryMasterSlavePairs } from '@services/redis/toolbox';

  import { LocalStorageKeys } from '@common/const';
  import { ipv4 } from '@common/regex';

  import DbStatus from '@components/db-status/index.vue';

  import type { SpecInfo } from '@views/redis/common/spec-panel/Index.vue';
  import { firstLetterToUpper } from '@views/redis/common/utils/index';

  import type { InstanceSelectorValues } from '../Index.vue';

  import { activePanelInjectionKey } from './PanelTab.vue';

  import type { TableProps } from '@/types/bkui-vue';
  interface TableItem {
    data: RedisHostModel
  }

  export interface Props {
    tableSettings: TableProps['settings'],
    lastValues: InstanceSelectorValues,
    node?: {
      id: number,
      name: string
      clusterDomain: string
    },
    role?: string,
    isRadioMode?: boolean,
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  export  interface ChoosedItem {
    bk_host_id: number;
    cluster_id: number;
    bk_cloud_id: number;
    ip: string;
    role: string;
    cluster_domain: string;
    spec_config: SpecInfo;
    instance_count?: number;
    slaveHost?: {
      faults: number;
      total: number;
    }
  }

  const props = withDefaults(defineProps<Props>(), {
    node: undefined,
    role: '',
    isRadioMode: false,
  });
  const emits = defineEmits<Emits>();


  const { t } = useI18n();
  const activePanel = inject(activePanelInjectionKey);


  const showTipLocalValue = localStorage.getItem(LocalStorageKeys.REDIS_DB_REPLACE_MASTER_TIP);

  const search = ref('');
  const isAnomalies = ref(false);
  const showMasterTip = ref(!showTipLocalValue);
  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
  });
  const isTableDataLoading = ref(false);
  const tableData = ref<RedisHostModel []>([]);
  const checkedMap = shallowRef<Record<string, ChoosedItem>>({});

  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item.ip]).length
  ));

  const isIndeterminate = computed(() => !isSelectedAll.value && Object.values(checkedMap.value).length > 0);

  const isSingleSelect = computed(() => props.isRadioMode);

  // 选中域名列表
  const selectedDomains = computed(() => Object.values(checkedMap.value).map(item => item.ip));

  const masterSlaveMap: Record<string, string> = {};

  const columns = [
    {
      width: 60,
      fixed: 'left',
      label: () => (isSingleSelect.value ? '' : (
        <bk-checkbox
          indeterminate={isIndeterminate.value}
          model-value={isSelectedAll.value}
          onClick={(e: Event) => e.stopPropagation()}
          onChange={handleSelectPageAll}
        />
      )),
      render: ({ index, data }: {index: number, data: RedisHostModel}) => {
        if (data.role === 'master' && showMasterTip.value) {
          return <bk-popover
            is-show={data.isShowTip}
            popover-delay={0}
            width={270}
            trigger="manual"
            theme="light"
            placement="top">
            {{
              default: () => (isSingleSelect.value ? (
                <bk-radio
                  class="check-box"
                  label={data.ip}
                  model-value={selectedDomains.value[0]}
                  onChange={() => handleTableSelectOne(true, data)}
                />
              ) : (
                <bk-checkbox
                  style="vertical-align:middle;padding-top:5px;"
                  model-value={Boolean(checkedMap.value[data.ip])}
                  onClick={(e: Event) => e.stopPropagation()}
                  onMouseenter={() => handleControlTip(index, true)}
                  onChange={(value: boolean) => handleTableSelectOne(value, data)}
                />
              )),
              content: () => (
                <div class="redis-host-master-tip-box">
                  <span>{t('选择 Master IP 会默认选上关联的 Slave IP，一同替换')}</span>
                  <div class="no-tip" onClick={handleClickNoTip}>{t('不再提示')}</div>
                </div>
              ),
            }}
          </bk-popover>;
        }
        return isSingleSelect.value ? (
          <bk-radio
            class="check-box"
            label={data.ip}
            model-value={selectedDomains.value[0]}
            onChange={() => handleTableSelectOne(true, data)}
          />
          ) : (
          <bk-checkbox
            style="vertical-align: middle;"
            model-value={Boolean(checkedMap.value[data.ip])}
            onClick={(e: Event) => e.stopPropagation()}
            onMouseenter={() => handleControlTip(index, false)}
            onChange={(value: boolean) => handleTableSelectOne(value, data)}
          />
        );
      },
    },
    {
      fixed: 'left',
      minWidth: 160,
      label: props.role ? props.role.charAt(0).toUpperCase() + props.role.slice(1) : t('实例'),
      field: 'ip',
    },
    {
      label: t('角色类型'),
      field: 'role',
      showOverflowTooltip: true,
      filter: {
        list: [{ text: 'master', value: 'master' }, { text: 'slave', value: 'slave' }, { text: 'proxy', value: 'proxy' }],
      },
      render: ({ data } : TableItem) => <span>{firstLetterToUpper(data.role)}</span>,
    },
    {
      label: t('实例状态'),
      field: 'status',
      render: ({ data } : TableItem) => {
        const info = data.host_info.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
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

  watch(() => props.lastValues, (lastValues) => {
    // 切换 tab 回显选中状态 \ 预览结果操作选中状态
    checkedMap.value = {};
    const checkedList = lastValues.idleHosts;
    for (const item of checkedList) {
      checkedMap.value[item.ip] = item;
    }
  }, { immediate: true, deep: true });

  watch(() => props.node, () => {
    if (props.node) {
      fetchData();
    }
  });

  const handleControlTip = (index: number, isMaster: boolean) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        isShowTip: false,
      });
    });
    if (isMaster) {
      tableData.value[index].isShowTip = true;
    }
  };

  const handleClickNoTip = () => {
    showMasterTip.value = false;
    localStorage.setItem(LocalStorageKeys.REDIS_DB_REPLACE_MASTER_TIP, '1');
  };

  const fetchData = () => {
    if (props.node) {
      isTableDataLoading.value = true;
      queryClusterHostList({
        cluster_id: props.node?.id,
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
    bk_host_id: data.bk_host_id,
    cluster_id: data.cluster_id,
    bk_cloud_id: data?.host_info?.cloud_id || 0,
    ip: data.ip || '',
    role: data.role,
    cluster_domain: props.node?.clusterDomain ?? '',
    spec_config: data.spec_config,
    instance_count: data.instance_count,
    slaveHost: {
      faults: data.unavailable_slave,
      total: data.total_slave,
    },
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
    const lastCheckMap = isSingleSelect.value ? {} : { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.ip] = formatValue(data);
      // master 与 slave 关联选择
      if (data.role === 'master') {
        const slaveIp = masterSlaveMap[data.ip];
        const slaveNode = tableData.value.filter(item => item.ip === slaveIp)[0];
        lastCheckMap[slaveIp] = formatValue(slaveNode);
      }
      if (isSingleSelect.value) {
        // 单选
        selectedDomains.value[0] = data.ip;
        checkedMap.value = lastCheckMap;
        triggerChange();
        return;
      }
    } else {
      if (isSingleSelect.value) {
        return;
      }
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
    handlePageValueChange(1);
    queryClusterHostList({
      ip: search.value,
    })
      .then((data) => {
        tableData.value = data;
        pagination.count = data.length;
        isAnomalies.value = false;
      })
      .catch(() => {
        tableData.value = [];
        pagination.count = 0;
        isAnomalies.value = true;
      })
      .finally(() => {
        isTableDataLoading.value = false;
      });
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

  .table-box {
    :deep(.check-box) {
      .bk-radio-label {
        display: none;
      }
    }
  }

  .redis-host-master-tip-box {
    word-break: break-all;

    .no-tip {
      width: 100%;
      font-weight: 400;
      color: #3A84FF;
      text-align: right;
      cursor: pointer;
    }
  }
</style>
