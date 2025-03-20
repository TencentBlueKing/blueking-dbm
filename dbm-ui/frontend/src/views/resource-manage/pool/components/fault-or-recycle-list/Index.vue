<template>
  <div class="fault-pool-container">
    <div class="operation-wrapper">
      <template v-if="isFaultPool">
        <BkButton
          :disabled="!selected.length"
          @click="handleBatchImport">
          {{ t('批量导入资源池') }}
        </BkButton>
        <BkButton
          class="ml-8"
          :disabled="!selected.length"
          @click="handleBatchConvertToRecyclePool">
          {{ t('批量转入回收池') }}
        </BkButton>
      </template>
      <BkButton
        v-else
        :disabled="!selected.length"
        @click="handleBatchRecycle">
        {{ t('批量回收') }}
      </BkButton>
      <BkDropdown class="ml-8">
        <BkButton>
          {{ t('复制') }}
          <DbIcon
            class="ml-8"
            type="down-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleCopySelectHost">{{ t('已选 IP') }}</BkDropdownItem>
            <BkDropdownItem @click="handleCopyAllHost">
              {{ `${t('所有 IP')}（${isFilter ? t('筛选后') : t('全量')}）` }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DbSearchSelect
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        unique-select
        :validate-values="validateSearchValues"
        value-behavior="need-key"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      class="table-box"
      :columns="tableColumn"
      :data-source="dataSource"
      primary-key="bk_host_id"
      remote-sort
      row-class="table-row"
      selectable
      :show-overflow="false"
      sort-type="ordering"
      @clear-search="handleClearSearch"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection" />
    <ReviewDataDialog
      v-model:is-show="isReviewDataDialogShow"
      :confirm-handler="handleRecycleSubmit"
      :selected="selected.map((item) => item.ip)"
      theme="danger"
      :tip="
        t('确认后，主机将从系统中删除，同时 CMDB 转移至「n」业务待回收，请谨慎操作！', {
          n: globalBizsStore.bizIdMap.get(defaultBizId)?.name,
        })
      "
      :title="t('确认批量回收 {n} 台主机？', { n: selected.length })"
      @success="handleRefresh" />
    <ReviewDataDialog
      v-model:is-show="isBatchConvertToRecyclePool"
      :confirm-handler="handleConvertSubmit"
      :selected="selected.map((item) => item.ip)"
      show-remark
      :tip="t('确认后，主机将标记为待回收，等待处理')"
      :title="t('确认批量将 {n} 台主机转入待回收池？', { n: selected.length })"
      @success="handleRefresh" />
    <ImportResourcePool
      v-model:is-show="isImportResourcePoolShow"
      :data="curImportData!"
      @refresh="handleRefresh" />
    <BatchImportResourcePool
      v-model:is-show="isBatchImportResourcePoolShow"
      :host-list="selected"
      @refresh="handleRefresh" />
  </div>
</template>

<script setup lang="tsx">
  import BkButton from 'bkui-vue/lib/button';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { getMachinePool, transferMachinePool } from '@services/source/dbdirty';
  import { fetchDeviceClass } from '@services/source/dbresourceResource';
  import { getUserList } from '@services/source/user';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { useGlobalBizs, useSystemEnviron } from '@stores';

  import DbStatus from '@components/db-status/index.vue';

  import OperationDetail from '@views/resource-manage/common/components/operation-detail/Index.vue';

  import { execCopy, getMenuListSearch, getSearchSelectorParams, messageWarn } from '@utils';

  import ReviewDataDialog from '../host-list/components/review-data-dialog/Index.vue';

  import BatchImportResourcePool from './components/BatchImportResourcePool/Index.vue';
  import ImportResourcePool from './components/ImportResourcePool.vue';

  const { t } = useI18n();
  const route = useRoute();
  const systemEnvironStore = useSystemEnviron();
  const globalBizsStore = useGlobalBizs();

  const {
    clearSearchValue,
    // columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    searchValue,
    // sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: [],
    fetchDataFn: () => fetchData(),
    searchType: 'resource_record',
  });

  const tableRef = useTemplateRef('tableRef');

  const selected = ref<FaultOrRecycleMachineModel[]>([]);
  const isReviewDataDialogShow = ref(false);
  const isImportResourcePoolShow = ref(false);
  const isBatchImportResourcePoolShow = ref(false);
  const isBatchConvertToRecyclePool = ref(false);
  const curImportData = ref<FaultOrRecycleMachineModel>();

  const defaultBizId = systemEnvironStore.urls.DBA_APP_BK_BIZ_ID;

  const tableColumn = [
    {
      field: 'ip',
      label: 'IP',
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.ip || '--',
      width: 160,
    },
    {
      field: 'agent_status',
      label: t('Agent状态'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => {
        const info =
          data.agent_status === 1
            ? {
                text: t('正常'),
                theme: 'success',
              }
            : {
                text: t('异常'),
                theme: 'danger',
              };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      field: 'city',
      label: t('地域'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.city || '--',
    },
    {
      field: 'sub_zone',
      label: t('园区'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.sub_zone || '--',
    },
    {
      field: 'rack_id',
      label: t('机架'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.rack_id || '--',
    },
    {
      field: 'os_name',
      label: t('操作系统名称'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.os_name || '--',
      width: 150,
    },
    {
      field: 'device_class',
      label: t('机型'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.device_class || '--',
    },
    {
      field: 'bk_cpu',
      label: t('CPU(核)'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.bk_cpu || '--',
    },
    {
      field: 'bkMemText',
      label: t('内存(G)'),
      showOverflow: true,
      width: 80,
    },
    {
      field: 'bk_disk',
      label: t('磁盘总容量(G)'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.bk_disk || '--',
    },
    {
      field: 'updateAtDisplay',
      label: t('转入时间'),
    },
    {
      field: 'updater',
      label: t('转入人'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.updater || '--',
      showOverflow: true,
      width: 100,
    },
    {
      field: 'latest_event',
      label: t('转入原因'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => <OperationDetail data={data.latest_event} />,
      width: 300,
    },
  ];

  const isFaultPool = computed(() => route.name === 'faultPool');
  const isFilter = computed(() => searchValue.value.length > 0);

  const searchSelectData = computed(() => [
    {
      id: 'ips',
      multiple: true,
      name: 'IP',
    },
    {
      id: 'city',
      name: t('地域'),
    },
    {
      id: 'sub_zone',
      name: t('园区'),
    },
    {
      id: 'rack_id',
      name: t('机架'),
    },
    {
      id: 'os_name',
      name: t('操作系统'),
    },
    {
      children: deviceClassList.value?.results.map((item) => ({
        id: String(item.id),
        name: item.device_type,
      })),
      id: 'device_class',
      name: t('机型'),
    },
  ]);

  const { data: deviceClassList } = useRequest(fetchDeviceClass);

  watch(searchValue, () => {
    fetchData();
  });

  watch(
    () => route.name,
    () => {
      searchValue.value = [];
      selected.value = [];
      nextTick(() => {
        tableRef.value!.clearSelected();
      });
    },
    {
      immediate: true,
    },
  );

  const getMenuList = async (item: ISearchItem | undefined, keyword: string) => {
    if (item?.id !== 'operator' && keyword) {
      return getMenuListSearch(item, keyword, searchSelectData.value, searchValue.value);
    }

    // 没有选中过滤标签
    if (!item) {
      // 过滤掉已经选过的标签
      const selected = (searchValue.value || []).map((value) => value.id);
      return searchSelectData.value.filter((item) => !selected.includes(item.id));
    }

    // 不需要远层加载
    return searchSelectData.value.find((set) => set.id === item.id)?.children || [];
  };

  // 清空搜索条件
  const handleClearSearch = () => {
    clearSearchValue();
  };

  const dataSource = (params: FaultOrRecycleMachineModel) =>
    getMachinePool({
      ...params,
      bk_biz_id: undefined,
      pool: isFaultPool.value ? 'fault' : 'recycle',
    });

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData(searchParams);
  };

  const handleSelection = (_data: FaultOrRecycleMachineModel, list: FaultOrRecycleMachineModel[]) => {
    selected.value = list;
  };

  const clearSelection = () => {
    tableRef.value!.clearSelected();
    selected.value = [];
  };

  const handleBatchImport = () => {
    isBatchImportResourcePoolShow.value = true;
  };

  const handleBatchRecycle = () => {
    isReviewDataDialogShow.value = true;
  };

  const handleBatchConvertToRecyclePool = () => {
    isBatchConvertToRecyclePool.value = true;
  };

  const handleRecycleSubmit = () => {
    return transferMachinePool({
      bk_host_ids: selected.value.map((item) => item.bk_host_id),
      source: 'recycle',
      target: 'recycled',
    });
  };

  const handleConvertSubmit = ({ remark }: { remark: string }) => {
    return transferMachinePool({
      bk_host_ids: selected.value.map((item) => item.bk_host_id),
      remark,
      source: 'fault',
      target: 'recycle',
    });
  };

  const handleCopyAllHost = () => {
    tableRef.value!.getAllData<FaultOrRecycleMachineModel>().then((data) => {
      if (data.length < 1) {
        messageWarn(t('暂无数据可复制'));
        return;
      }
      const ipList = data.map((item) => item.ip);
      execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
    });
  };

  const handleCopySelectHost = () => {
    const ipList = selected.value.map((item) => item.ip);
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
  };

  const handleRefresh = () => {
    clearSelection();
    fetchData();
  };

  onMounted(() => {
    fetchData();
  });
</script>

<style lang="less" scoped>
  .fault-pool-container {
    .operation-wrapper {
      display: flex;
      align-items: center;
      margin-bottom: 16px;

      .pool-search-selector {
        width: 560px;
        margin-left: auto;
      }
    }
  }
</style>

<style lang="less">
  .pool-recycle-pop-confirm-content {
    font-size: 12px;
    color: #63656e;

    .ip {
      color: #313238;
    }

    .tip {
      margin-top: 4px;
      margin-bottom: 14px;
    }
  }
</style>
