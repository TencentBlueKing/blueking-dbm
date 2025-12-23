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
              {{ `${t('所有 IP')}（${isSearching ? t('筛选后') : t('全量')}）` }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="bk_host_id"
      selectable
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <TableColumn
        col-key="ips"
        :filter="columnFilter?.ips"
        fixed="left"
        title="IP"
        :width="150">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.ip || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="agent_status"
        :title="t('Agent 状态')"
        :width="110">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          <DbStatus :theme="row.statusInfo.theme">{{ row.statusInfo.text }}</DbStatus>
        </template>
      </TableColumn>
      <TableColumn
        col-key="city"
        :filter="columnFilter?.city"
        :title="t('地域')"
        :width="80">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.city || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="sub_zone"
        :filter="columnFilter?.sub_zone"
        :title="t('园区')"
        :width="90">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.sub_zone || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="rack_id"
        :filter="columnFilter?.rack_id"
        :title="t('机架')"
        :width="80">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.rack_id || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="os_name"
        :filter="columnFilter?.os_name"
        :title="t('操作系统名称')"
        :width="150">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.os_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="device_class"
        :filter="columnFilter?.device_class"
        :title="t('机型')"
        :width="130">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.device_class || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_cpu"
        :title="t('CPU(核)')">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.bk_cpu || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bkMemText"
        :min-width="90"
        :title="t('内存(G)')">
      </TableColumn>
      <TableColumn
        col-key="bk_disk"
        :title="t('磁盘总容量(G)')"
        :width="110">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.bk_disk || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="updateAtDisplay"
        :filter="columnFilter?.update_at"
        :title="t('转入时间')"
        :width="180">
      </TableColumn>
      <TableColumn
        col-key="updater"
        :filter="columnFilter?.updater"
        :title="t('转入人')"
        :width="120">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.updater || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="latest_event"
        :title="t('转入原因')"
        :width="300">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          <OperationDetail :data="row.latest_event" />
        </template>
      </TableColumn>
    </DbTable>
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
    <!-- <ImportResourcePool
      v-model:is-show="isImportResourcePoolShow"
      :data="curImportData!"
      @refresh="handleRefresh" /> -->
    <BatchImportResourcePool
      v-model:is-show="isBatchImportResourcePoolShow"
      :host-list="selected"
      @refresh="handleRefresh" />
  </div>
</template>

<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import BkButton from 'bkui-vue/lib/button';
  import { useI18n } from 'vue-i18n';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { getMachinePool, transferMachinePool } from '@services/source/dbdirty';

  import { useGlobalBizs, useSystemEnviron } from '@stores';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import OperationDetail from '@views/resource-manage/common/components/operation-detail/Index.vue';
  import ReviewDataDialog from '@views/resource-manage/common/components/review-data-dialog/Index.vue';
  import { useColumnFilter } from '@views/resource-manage/common/hooks/useColumnFilter';
  import { useQuickSearch } from '@views/resource-manage/common/hooks/useQuickSearch';

  import { checkDbConsole, execCopy, messageSuccess, messageWarn } from '@utils';

  import BatchImportResourcePool from './components/BatchImportResourcePool/Index.vue';

  const { t } = useI18n();
  const route = useRoute();
  const systemEnvironStore = useSystemEnviron();
  const globalBizsStore = useGlobalBizs();

  const isFaultPool = route.name === 'faultPool';
  const pool = isFaultPool ? 'fault' : 'recycle';
  const { isSearching, quickSearchData, quickSearchValue } = useQuickSearch(pool);
  const { data: columnFilter } = useColumnFilter(pool);

  const tableRef = useTemplateRef('tableRef');

  const selected = ref<FaultOrRecycleMachineModel[]>([]);
  const isReviewDataDialogShow = ref(false);
  const isBatchImportResourcePoolShow = ref(false);
  const isBatchConvertToRecyclePool = ref(false);
  const hcmRecycle = ref(true);

  const defaultBizId = systemEnvironStore.urls.RESOURCE_INDEPENDENT_BIZ;

  watch(
    () => route.name,
    () => {
      quickSearchValue.value = {};
      selected.value = [];
      nextTick(() => {
        tableRef.value!.clearSelected();
      });
    },
    {
      immediate: true,
    },
  );

  const dataSource = (params: ServiceParameters<typeof getMachinePool>) =>
    getMachinePool({
      ...params,
      pool,
    });

  const fetchData = () => {
    tableRef.value!.fetchData(quickSearchValue.value);
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, any>) => {
    quickSearchValue.value = filterValue;
  };

  const handleSelection = (_key: string[], list: FaultOrRecycleMachineModel[]) => {
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
    tableRef.value!.fetchAllData<FaultOrRecycleMachineModel>().then((data) => {
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
      const { BK_HCM_URL, RESOURCE_INDEPENDENT_BIZ } = systemEnvironStore.urls;
      const targetHref = `${BK_HCM_URL}/#/business/applications?bizs=${RESOURCE_INDEPENDENT_BIZ}&filter=order_id=${data.hcm_recycle_id}&type=host_recycle`;
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
