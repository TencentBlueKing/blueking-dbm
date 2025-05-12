<template>
  <div class="fault-pool-container">
    <BkAlert
      class="mb-12"
      closable
      :title="
        isFaultPool
          ? t('用来暂存故障主机，已下架的主机若检测有关联uwork、xwork单据将自动转入故障池等待后续处理')
          : t('集中存放待回收的主机，已下架的主机若检测为Windows、待裁撤主机将自动转入待回收池以便执行回收操作')
      " />
    <div class="operation-wrapper">
      <template v-if="isFaultPool">
        <AuthButton
          action-id="resource_pool_manage"
          :disabled="!selected.length"
          @click="handleBatchImport">
          {{ t('批量导入资源池') }}
        </AuthButton>
        <AuthButton
          action-id="resource_pool_manage"
          class="ml-8"
          :disabled="!selected.length"
          @click="handleBatchConvertToRecyclePool">
          {{ t('批量转入回收池') }}
        </AuthButton>
      </template>
      <AuthButton
        v-else
        action-id="resource_pool_manage"
        :disabled="!selected.length"
        @click="handleBatchRecycle">
        {{ t('批量回收') }}
      </AuthButton>
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
      <BkDatePicker
        v-model="dateRange"
        append-to-body
        :placeholder="t('请选择转入时间范围')"
        style="width: 350px; margin-left: auto"
        type="datetimerange"
        @change="fetchData" />
      <DbSearchSelect
        :data="searchSelectData"
        :get-menu-list="getMenuList"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: 8px"
        unique-select
        :validate-values="validateSearchValues"
        value-behavior="need-key"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      class="table-box"
      :columns="tableColumn"
      :data-source="getMachinePool"
      primary-key="bk_host_id"
      releate-url-query
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
      @success="handleRecycleRefresh">
      <template #append>
        <BkCheckbox
          v-model="hcmRecycle"
          v-db-console="'common.hcmRecycle'"
          class="mt-12">
          {{ t('勾选后，自动在「海垒」创建回收单据') }}
        </BkCheckbox>
      </template>
    </ReviewDataDialog>
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
  import { Message } from 'bkui-vue';
  import BkButton from 'bkui-vue/lib/button';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { getMachinePool, transferMachinePool } from '@services/source/dbdirty';
  import { fetchDeviceClass } from '@services/source/dbresourceResource';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { useGlobalBizs, useSystemEnviron } from '@stores';

  import DbStatus from '@components/db-status/index.vue';

  import OperationDetail from '@views/resource-manage/common/components/operation-detail/Index.vue';

  import {
    checkDbConsole,
    execCopy,
    getMenuListSearch,
    getSearchSelectorParams,
    messageSuccess,
    messageWarn,
  } from '@utils';

  import ReviewDataDialog from '../host-list/components/review-data-dialog/Index.vue';

  import BatchImportResourcePool from './components/BatchImportResourcePool/Index.vue';
  import ImportResourcePool from './components/ImportResourcePool.vue';

  // const initDate = () => {
  //   const startTime = dayjs().subtract(7, 'day').format('YYYY-MM-DD HH:mm:ss');
  //   const endTime = dayjs().format('YYYY-MM-DD HH:mm:ss');
  //   return [startTime, endTime] as [string, string];
  // };

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
  const dateRange = ref(['', ''] as [string, string]);
  const hcmRecycle = ref(true);

  const defaultBizId = systemEnvironStore.urls.DBA_APP_BK_BIZ_ID;

  const tableColumn = [
    {
      field: 'ip',
      fixed: 'left',
      label: 'IP',
      minWidth: 130,
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
      width: 100,
    },
    {
      field: 'city',
      label: t('地域'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.city || '--',
      showOverflow: true,
      width: 80,
    },
    {
      field: 'sub_zone',
      label: t('园区'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.sub_zone || '--',
      showOverflow: true,
      width: 90,
    },
    {
      field: 'rack_id',
      label: t('机架'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.rack_id || '--',
      showOverflow: true,
      width: 80,
    },
    {
      field: 'os_name',
      label: t('操作系统名称'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.os_name || '--',
      showOverflow: true,
      width: 150,
    },
    {
      field: 'device_class',
      label: t('机型'),
      minWidth: 130,
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.device_class || '--',
      showOverflow: true,
    },
    {
      field: 'bk_cpu',
      label: t('CPU(核)'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.bk_cpu || '--',
    },
    {
      field: 'bkMemText',
      label: t('内存(G)'),
      minWidth: 90,
      showOverflow: true,
    },
    {
      field: 'bk_disk',
      label: t('磁盘总容量(G)'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.bk_disk || '--',
      width: 110,
    },
    {
      field: 'updateAtDisplay',
      label: t('转入时间'),
      width: 180,
    },
    {
      field: 'updater',
      label: t('转入人'),
      render: ({ data }: { data: FaultOrRecycleMachineModel }) => data.updater || '--',
      showOverflow: true,
      width: 120,
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
      id: 'updater',
      name: t('转入人'),
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
    dateRange.value = ['', ''];
  };

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    const [beginTime, endTime] = dateRange.value;

    tableRef.value?.fetchData({
      ...searchParams,
      // ...sortValue,
      bk_biz_id: undefined,
      pool: isFaultPool.value ? 'fault' : 'recycle',
      update_at__gte: beginTime ? dayjs(beginTime).format('YYYY-MM-DD HH:mm:ss') : '',
      update_at__lte: endTime ? dayjs(endTime).format('YYYY-MM-DD HH:mm:ss') : '',
    });
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
    const params: ServiceParameters<typeof transferMachinePool> = {
      bk_host_ids: selected.value.map((item) => item.bk_host_id),
      source: 'recycle',
      target: 'recycled',
    };
    if (checkDbConsole('common.hcmRecycle')) {
      params.hcm_recycle = hcmRecycle.value;
    }
    return transferMachinePool(params);
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

  const handleRecycleRefresh = (data: ServiceReturnType<typeof transferMachinePool>) => {
    if (checkDbConsole('common.hcmRecycle') && data.hcm_recycle_id) {
      const { BK_HCM_URL, DBA_APP_BK_BIZ_ID } = systemEnvironStore.urls;
      const targetHref = `${BK_HCM_URL}/#/business/applications?bizs=${DBA_APP_BK_BIZ_ID}&filter=order_id=${data.hcm_recycle_id}&type=host_recycle`;
      Message({
        actions: [
          {
            disabled: true,
            id: 'details',
          },
          {
            disabled: true,
            id: 'fix',
          },
          {
            id: 'assistant',
            render: () =>
              h(
                'a',
                {
                  href: targetHref,
                  target: '_blank',
                },
                ` ${t('查看详情')}`,
              ),
          },
        ],
        delay: 6000,
        dismissable: false,
        message: {
          code: '',
          overview: data.message,
          suggestion: '',
        },
        theme: 'success',
      });
    } else {
      messageSuccess(data.message);
    }

    hcmRecycle.value = true;
    handleRefresh();
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
