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
    <SerachBar
      v-model="searchValue"
      is-host
      :placeholder="t('请输入或选择条件搜索')"
      :search-attrs="searchAttrs"
      :type="ClusterTypes.REDIS"
      :validate-search-values="validateSearchValues"
      @search-value-change="handleSearchValueChange" />
    <BkLoading
      :loading="isTableDataLoading"
      :z-index="2">
      <DbOriginalTable
        class="table-box"
        :columns="columns"
        :data="tableData"
        :is-anomalies="isAnomalies"
        :is-searching="!!searchValue.length"
        :max-height="530"
        :pagination="pagination.count < 10 ? false : pagination"
        remote-pagination
        :settings="tableSettings"
        style="margin-top: 12px"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getRedisMachineList } from '@services/source/redis';
  import type { queryMasterSlavePairs } from '@services/source/redisToolbox';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { ClusterTypes, LocalStorageKeys } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import SerachBar from '@components/instance-selector/components/common/SearchBar.vue';

  import type { SpecInfo } from '@views/db-manage/redis/common/spec-panel/Index.vue';

  import { getSearchSelectorParams } from '@utils';

  import type { InstanceSelectorValues } from '../Index.vue';

  import { activePanelInjectionKey } from './PanelTab.vue';

  type RedisHostModel = {
    isShowTip?: boolean;
  } & ServiceReturnType<typeof getRedisMachineList>['results'][number];

  interface TableItem {
    data: RedisHostModel;
  }

  export interface Props {
    isRadioMode?: boolean;
    lastValues: InstanceSelectorValues;
    masterSlaveMap?: Record<string, ServiceReturnType<typeof queryMasterSlavePairs>[number]>;
    node?: {
      id: number;
      name: string;
      obj: 'biz' | 'cluster';
    };
    tableSettings: InstanceType<typeof Table>['$props'];
  }

  type Emits = (e: 'change', value: InstanceSelectorValues) => void;

  export interface ChoosedItem {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    cluster_domain: string;
    cluster_ids: number[];
    ip: string;
    role: string;
    spec_config: SpecInfo;
  }

  const props = withDefaults(defineProps<Props>(), {
    isRadioMode: false,
    masterSlaveMap: () => ({}),
    node: undefined,
    role: '',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const {
    clearSearchValue,
    columnAttrs,
    columnCheckedMap,
    columnFilterChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['bk_cloud_id'],
    defaultSearchItem: {
      id: 'ip',
      name: 'IP',
    },
    fetchDataFn: () => fetchData(),
    isDiscardNondefault: true,
    searchType: ClusterTypes.REDIS,
  });

  const activePanel = inject(activePanelInjectionKey);

  const showTipLocalValue = localStorage.getItem(LocalStorageKeys.REDIS_DB_REPLACE_MASTER_TIP);

  const isAnomalies = ref(false);
  const showMasterTip = ref(!showTipLocalValue);
  const isTableDataLoading = ref(false);
  const tableData = ref<RedisHostModel[]>([]);

  const checkedMap = shallowRef<Record<string, ChoosedItem>>({});

  const pagination = reactive({
    align: 'right',
    count: 0,
    current: 1,
    layout: ['total', 'limit', 'list'],
    limit: 10,
    limitList: [10, 20, 50, 100],
  });

  const isSelectedAll = computed(
    () =>
      tableData.value.length > 0 &&
      tableData.value.length === tableData.value.filter((item) => checkedMap.value[item.ip]).length,
  );

  const isIndeterminate = computed(() => !isSelectedAll.value && Object.values(checkedMap.value).length > 0);

  const isSingleSelect = computed(() => props.isRadioMode);

  // 选中域名列表
  const selectedDomains = computed(() => Object.values(checkedMap.value).map((item) => item.ip));

  const columns = computed(() => [
    {
      fixed: 'left',
      label: () =>
        isSingleSelect.value ? (
          ''
        ) : (
          <div style='display:flex;align-items:center'>
            <bk-checkbox
              indeterminate={isIndeterminate.value}
              model-value={isSelectedAll.value}
              onChange={handleSelectPageAll}
            />
            <bk-popover
              v-slots={{
                content: () => (
                  <div class='db-table-select-plan'>
                    <div
                      class='item'
                      onClick={handleWholeSelect}>
                      {t('跨页全选')}
                    </div>
                  </div>
                ),
                default: () => (
                  <db-icon
                    class='select-menu-flag ml-10'
                    type='down-big'
                  />
                ),
              }}
              arrow={false}
              placement='bottom-start'
              theme='light db-table-select-menu'
              trigger='hover'></bk-popover>
          </div>
        ),
      render: ({ data, index }: { data: RedisHostModel; index: number }) => {
        if (data.instance_role === 'redis_master' && showMasterTip.value) {
          return (
            <bk-popover
              is-show={data.isShowTip}
              placement='top'
              popover-delay={0}
              theme='light'
              trigger='manual'
              width={270}>
              {{
                content: () => (
                  <div class='redis-host-master-tip-box'>
                    <span>{t('选择 Master IP 会默认选上关联的 Slave IP，一同替换')}</span>
                    <div
                      class='no-tip'
                      onClick={handleClickNoTip}>
                      {t('不再提示')}
                    </div>
                  </div>
                ),
                default: () =>
                  isSingleSelect.value ? (
                    <bk-radio
                      class='check-box'
                      label={data.ip}
                      model-value={selectedDomains.value[0]}
                      onChange={() => handleTableSelectOne(true, data)}
                    />
                  ) : (
                    <bk-checkbox
                      model-value={Boolean(checkedMap.value[data.ip])}
                      style='vertical-align:middle;padding-top:5px;'
                      onChange={(value: boolean) => handleTableSelectOne(value, data)}
                      onMouseenter={() => handleControlTip(index, true)}
                    />
                  ),
              }}
            </bk-popover>
          );
        }
        return isSingleSelect.value ? (
          <bk-radio
            class='check-box'
            label={data.ip}
            model-value={selectedDomains.value[0]}
            onChange={() => handleTableSelectOne(true, data)}
          />
        ) : (
          <bk-checkbox
            model-value={Boolean(checkedMap.value[data.ip])}
            style='vertical-align: middle;'
            onChange={(value: boolean) => handleTableSelectOne(value, data)}
            onClick={(e: Event) => e.stopPropagation()}
            onMouseenter={() => handleControlTip(index, false)}
          />
        );
      },
      width: 70,
    },
    {
      field: 'ip',
      fixed: 'left',
      label: 'IP',
      minWidth: 160,
    },
    {
      field: 'instance_role',
      filter: {
        checked: columnCheckedMap.value.role,
        list: [
          { text: 'redis_master', value: 'redis_master' },
          { text: 'redis_slave', value: 'redis_slave' },
          { text: 'proxy', value: 'proxy' },
        ],
      },
      label: t('角色类型'),
      render: ({ data }: TableItem) => <span>{data.instance_role}</span>,
      showOverflowTooltip: true,
    },
    {
      field: 'status',
      label: t('实例状态'),
      render: ({ data }: TableItem) => {
        const info =
          data.host_info.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      field: 'bk_cloud_id',
      filter: {
        checked: columnCheckedMap.value.bk_cloud_id,
        list: columnAttrs.value.bk_cloud_id,
      },
      label: t('管控区域'),
      minWidth: 100,
      render: ({ data }: TableItem) => <span>{data.bk_cloud_name ?? '--'}</span>,
    },
    {
      field: 'alive',
      label: t('Agent状态'),
      minWidth: 100,
      render: ({ data }: TableItem) => {
        const info =
          data.host_info?.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      field: 'host_name',
      label: t('主机名称'),
      render: ({ data }: TableItem) => data.host_info?.host_name || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'os_name',
      label: t('OS名称'),
      render: ({ data }: TableItem) => data.host_info?.os_name || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'cloud_vendor',
      label: t('所属云厂商'),
      render: ({ data }: TableItem) => data.host_info?.cloud_vendor || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'os_type',
      label: t('OS类型'),
      render: ({ data }: TableItem) => data.host_info?.os_type || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'host_id',
      label: t('主机ID'),
      render: ({ data }: TableItem) => data.host_info?.host_id || '--',
      showOverflowTooltip: true,
    },
    {
      field: 'agent_id',
      label: 'Agent ID',
      render: ({ data }: TableItem) => data.host_info?.agent_id || '--',
      showOverflowTooltip: true,
    },
  ]);

  watch(
    () => props.lastValues,
    (lastValues) => {
      // 切换 tab 回显选中状态 \ 预览结果操作选中状态
      checkedMap.value = {};
      const checkedList = lastValues.idleHosts;
      for (const item of checkedList) {
        checkedMap.value[item.ip] = item;
      }
    },
    { deep: true, immediate: true },
  );

  watch(
    () => props.node,
    () => {
      if (props.node) {
        fetchData();
      }
    },
  );

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

  const generateParams = () => ({
    extra: 1,
    limit: pagination.limit,
    offset: (pagination.current - 1) * pagination.limit,
    ...getSearchSelectorParams(searchValue.value),
    ...(props.node?.obj === 'cluster' && {
      cluster_ids: `${props.node.id}`,
    }),
  });

  // 跨页全选
  const handleWholeSelect = () => {
    isTableDataLoading.value = true;
    const params = generateParams();
    params.limit = -1;
    getRedisMachineList(params)
      .then((data) => {
        data.results.forEach((dataItem) => {
          handleTableSelectOne(true, dataItem);
        });
      })
      .finally(() => (isTableDataLoading.value = false));
  };

  const fetchData = () => {
    if (props.node) {
      isTableDataLoading.value = true;
      const params = generateParams();
      getRedisMachineList(params)
        .then((data) => {
          tableData.value = data.results.map((item) =>
            Object.assign(item, {
              isShowTip: false,
            }),
          );
          pagination.count = data.count;
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
    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    bk_cloud_id: data?.host_info?.cloud_id || 0,
    bk_host_id: data?.bk_host_id || 0,
    cluster_domain: data.related_clusters[0]?.immute_domain ?? '',
    cluster_ids: data.related_clusters.map((item) => item.id) || [],
    ip: data?.ip || '',
    role: data?.instance_role || '',
    spec_config: data?.spec_config || null,
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

  const handleTableSelectOne = async (checked: boolean, data: RedisHostModel) => {
    const lastCheckMap = isSingleSelect.value ? {} : { ...checkedMap.value };
    if (checked) {
      lastCheckMap[data.ip] = formatValue(data);
      // master 与 slave 关联选择
      if (Object.keys(props.masterSlaveMap).length > 0 && data.instance_role === 'redis_master') {
        if (props.masterSlaveMap[data.ip]) {
          const { slave_ip: slaveIp, slaves } = props.masterSlaveMap[data.ip];
          lastCheckMap[slaveIp] = _.merge(formatValue(data), {
            bk_host_id: slaves.bk_host_id,
            ip: slaves.ip,
            role: 'redis_slave',
          });
        }
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

  // 切换每页条数
  const handlePageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    handlePageValueChange(1);
  };
  // 切换页码
  const handlePageValueChange = (pageValue: number) => {
    pagination.current = pageValue;
    fetchData();
  };
</script>

<style lang="less">
  .instance-selector-render-topo-host {
    padding: 0 24px;
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
      color: #3a84ff;
      text-align: right;
      cursor: pointer;
    }
  }
</style>
