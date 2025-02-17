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
        :show-overflow="false"
        style="margin-top: 12px"
        @clear-search="clearSearchValue"
        @column-filter="columnFilterChange"
        @page-limit-change="handlePageLimitChange"
        @page-value-change="handlePageValueChange" />
    </BkLoading>
  </div>
</template>
<script setup lang="tsx">
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

  type RedisHostModel = ServiceReturnType<typeof getRedisMachineList>['results'][number] & {
    isShowTip?: boolean;
  };

  interface TableItem {
    data: RedisHostModel
  }

  export interface Props {
    lastValues: InstanceSelectorValues,
    node?: {
      id: number,
      name: string
      obj: 'biz' | 'cluster'
    },
    role?: string,
    isRadioMode?: boolean,
    masterSlaveMap?: Record<string, ServiceReturnType<typeof queryMasterSlavePairs>[number]>,
  }

  interface Emits {
    (e: 'change', value: InstanceSelectorValues): void;
  }

  export  interface ChoosedItem {
    bk_host_id: number;
    bk_cloud_id: number;
    ip: string;
    role: string;
    cluster_domain: string;
    spec_config: SpecInfo;
  }

  const props = withDefaults(defineProps<Props>(), {
    node: undefined,
    role: '',
    isRadioMode: false,
    masterSlaveMap: () => ({}),
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const {
    columnAttrs,
    searchAttrs,
    searchValue,
    columnCheckedMap,
    columnFilterChange,
    clearSearchValue,
    validateSearchValues,
    handleSearchValueChange,
  } = useLinkQueryColumnSerach({
    searchType: ClusterTypes.REDIS,
    attrs: [
      'bk_cloud_id'
    ],
    fetchDataFn: () => fetchData(),
    defaultSearchItem: {
      name: 'IP',
      id: 'ip',
    },
    isDiscardNondefault: true,
  });

  const activePanel = inject(activePanelInjectionKey);

  const showTipLocalValue = localStorage.getItem(LocalStorageKeys.REDIS_DB_REPLACE_MASTER_TIP);

  const isAnomalies = ref(false);
  const showMasterTip = ref(!showTipLocalValue);
  const isTableDataLoading = ref(false);
  const tableData = ref<RedisHostModel[]>([]);

  const checkedMap = shallowRef<Record<string, ChoosedItem>>({});

  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    limitList: [10, 20, 50, 100],
    align: 'right',
    layout: ['total', 'limit', 'list'],
    remote: true
  });

  const isSelectedAll = computed(() => (
    tableData.value.length > 0
    && tableData.value.length === tableData.value.filter(item => checkedMap.value[item.ip]).length
  ));

  const isIndeterminate = computed(() => !isSelectedAll.value && Object.values(checkedMap.value).length > 0);

  const isSingleSelect = computed(() => props.isRadioMode);

  // 选中域名列表
  const selectedDomains = computed(() => Object.values(checkedMap.value).map(item => item.ip));

  const columns = computed(() => [
    {
      width: 70,
      fixed: 'left',
      label: () => (isSingleSelect.value ? '' : (
        <div style="display:flex;align-items:center">
          <bk-checkbox
            indeterminate={isIndeterminate.value}
            model-value={isSelectedAll.value}
            onChange={handleSelectPageAll}
          />
          <bk-popover
            placement="bottom-start"
            theme="light db-table-select-menu"
            arrow={ false }
            trigger='hover'
            v-slots={{
              default: () => <db-icon class="select-menu-flag ml-10" type="down-big" />,
              content: () => (
                <div class="db-table-select-plan">
                  <div
                    class="item"
                    onClick={handleWholeSelect}>{t('跨页全选')}</div>
                </div>
              ),
            }}>
          </bk-popover>
        </div>
      )),
      render: ({ index, data }: {index: number, data: RedisHostModel}) => {
        if (data.instance_role === 'redis_master' && showMasterTip.value) {
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
      field: 'instance_role',
      showOverflow: true,
      render: ({ data } : TableItem) => <span>{data.instance_role}</span>,
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
      label: t('园区'),
      field: 'bk_sub_zone',
      minWidth: 120,
      showOverflow: true,
      render: ({ data }: TableItem) => data.bk_sub_zone || '--',
    },
    {
      label: t('机架ID'),
      field: 'bk_rack_id',
      minWidth: 80,
      showOverflow: true,
      render: ({ data }: TableItem) => data.bk_rack_id || '--',
    },
    {
      label: t('机型'),
      field: 'bk_svr_device_cls_name',
      minWidth: 120,
      showOverflow: true,
      render: ({ data }: TableItem) => data.bk_svr_device_cls_name || '--',
    },
    {
      minWidth: 100,
      label: t('管控区域'),
      field: 'bk_cloud_id',
      filter: {
        list: columnAttrs.value.bk_cloud_id,
        checked: columnCheckedMap.value.bk_cloud_id,
      },
      render: ({ data }: TableItem) => <span>{data.bk_cloud_name ?? '--'}</span>,
    },
    {
      minWidth: 100,
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data } : TableItem) => {
        const info = data.host_info?.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('主机名称'),
      field: 'host_name',
      showOverflow: true,
      minWidth: 150,
      render: ({ data } : TableItem) => data.host_info?.host_name || '--',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
      showOverflow: true,
      minWidth: 150,
      render: ({ data } : TableItem) => data.host_info?.os_name || '--',
    },
    {
      label: t('所属云厂商'),
      field: 'cloud_vendor',
      showOverflow: true,
      render: ({ data }: TableItem) => data.host_info?.cloud_vendor || '--',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
      showOverflow: true,
      render: ({ data }: TableItem) => data.host_info?.os_type || '--',
    },
    {
      label: t('主机ID'),
      field: 'host_id',
      showOverflow: true,
      render: ({ data } : TableItem) => data.host_info?.host_id || '--',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
      showOverflow: true,
      render: ({ data } : TableItem) => data.host_info?.agent_id || '--',
    },
  ]);

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

  const generateParams = () => ({
    limit: pagination.limit,
    offset: (pagination.current - 1) * pagination.limit,
    extra: 1,
    ...getSearchSelectorParams(searchValue.value),
    ...(props.node?.obj === 'cluster' && {
      cluster_ids: `${props.node.id}`,
    }),
  })

  // 跨页全选
  const handleWholeSelect = () => {
    isTableDataLoading.value = true;
    const params = generateParams();
    params.limit = -1;
    getRedisMachineList(params).then((data) => {
      data.results.forEach((dataItem) => {
        handleTableSelectOne(true, dataItem);
      });
    }).finally(() => isTableDataLoading.value = false);
  };

  const fetchData = () => {
    if (props.node) {
      isTableDataLoading.value = true;
      const params = generateParams();
      getRedisMachineList(params)
        .then((data) => {
          tableData.value = data.results.map(item => Object.assign(item, {
            isShowTip: false,
          }));
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
    bk_host_id: data?.bk_host_id || 0,
    bk_cloud_id: data?.host_info?.cloud_id || 0,
    ip: data?.ip || '',
    role: data?.instance_role || '',
    cluster_domain: props.node?.name ?? '',
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
        const {slave_ip: slaveIp, slaves } = props.masterSlaveMap[data.ip];
        lastCheckMap[slaveIp] = {
          ...formatValue(data),
          ...slaves,
          role: 'redis_slave',
        };
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
  const handlePageValueChange = (pageValue:number) => {
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
