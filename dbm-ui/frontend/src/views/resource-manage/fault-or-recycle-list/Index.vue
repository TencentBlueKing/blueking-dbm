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
      <template v-else>
        <AuthButton
          v-db-console="'common.hcmRecycle'"
          action-id="resource_pool_manage"
          class="mr-8"
          :disabled="!selected.length"
          theme="primary"
          @click="handleBatchRecycle">
          {{ t('批量回收') }}
        </AuthButton>
        <AuthButton
          action-id="resource_pool_manage"
          :disabled="!selected.length"
          @click="handleBatchDelete">
          {{ t('批量删除') }}
        </AuthButton>
      </template>
      <BkDropdown
        class="ml-8"
        :popover-options="{
          clickContentAutoHide: true,
        }"
        trigger="click">
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
        :title="t('CPU（核）')">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.bk_cpu || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bkMemText"
        :min-width="90"
        :title="t('内存（G）')" />
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
      v-model:is-show="isBatchRecycleShow"
      :confirm-handler="handleRecycleSubmit"
      :selected="selected.map((item) => item.ip)"
      theme="danger"
      :tip="t('确认后，主机将从系统中删除主机记录并自动在「海垒」创建回收单据，请谨慎操作！')"
      :title="t('确认批量回收 {n} 台主机？', { n: selected.length })"
      @success="handleRecycleRefresh">
    </ReviewDataDialog>
    <ReviewDataDialog
      v-model:is-show="isBatchDeleteShow"
      :confirm-handler="handleDeleteSubmit"
      :selected="selected.map((item) => item.ip)"
      theme="danger"
      :tip="t('确认后，主机将从系统中删除主机记录，请谨慎操作！')"
      :title="t('确认批量删除 {n} 台主机？', { n: selected.length })"
      @success="handleDeleteRefresh">
    </ReviewDataDialog>
    <ReviewDataDialog
      v-model:is-show="isBatchConvertToRecyclePool"
      :confirm-handler="handleConvertSubmit"
      :selected="selected.map((item) => item.ip)"
      show-remark
      :tip="t('确认后，主机将标记为待回收，等待处理')"
      :title="t('确认批量将 {n} 台主机转入待回收池？', { n: selected.length })"
      @success="handleRefresh" />
    <BatchImportResourcePool
      v-model:is-show="isBatchImportResourcePoolShow"
      :host-list="selected"
      @refresh="handleRefresh" />
  </div>
</template>

<script setup lang="tsx">
  import BkButton from 'bkui-vue/lib/button';
  import { useI18n } from 'vue-i18n';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { getMachinePool, transferMachinePool } from '@services/source/dbdirty';

  import DbStatus from '@components/db-status/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import BatchImportResourcePool from '@views/resource-manage/common/components/fault-pool-batch-import/Index.vue';
  import OperationDetail from '@views/resource-manage/common/components/operation-detail/Index.vue';
  import ReviewDataDialog from '@views/resource-manage/common/components/review-data-dialog/Index.vue';
  import { useColumnFilter } from '@views/resource-manage/common/hooks/useColumnFilter';
  import { useQuickSearch } from '@views/resource-manage/common/hooks/useQuickSearch';
  import { useRecycleRefresh } from '@views/resource-manage/common/hooks/useRecycleRefresh';

  import { execCopy, messageWarn } from '@utils';

  const { t } = useI18n();
  const route = useRoute();

  const isFaultPool = route.name === 'faultPool';
  const pool = isFaultPool ? 'fault' : 'recycle';
  const { isSearching, quickSearchData, quickSearchValue } = useQuickSearch(pool);
  const { data: columnFilter } = useColumnFilter(pool);
  const { handleRecycleRefresh } = useRecycleRefresh({
    onSucess() {
      handleRefresh();
    },
  });

  const tableRef = useTemplateRef('tableRef');

  const selected = ref<FaultOrRecycleMachineModel[]>([]);
  const isBatchRecycleShow = ref(false);
  const isBatchDeleteShow = ref(false);
  const isBatchImportResourcePoolShow = ref(false);
  const isBatchConvertToRecyclePool = ref(false);

  // watch(
  //   () => route.name,
  //   () => {
  //     quickSearchValue.value = {};
  //     selected.value = [];
  //     nextTick(() => {
  //       tableRef.value!.clearSelected();
  //     });
  //   },
  //   {
  //     immediate: true,
  //   },
  // );

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

  // const clearSelection = () => {
  //   tableRef.value!.clearSelected();
  //   selected.value = [];
  // };

  const handleBatchImport = () => {
    isBatchImportResourcePoolShow.value = true;
  };

  const handleBatchRecycle = () => {
    isBatchRecycleShow.value = true;
  };

  const handleBatchDelete = () => {
    isBatchDeleteShow.value = true;
  };

  const handleBatchConvertToRecyclePool = () => {
    isBatchConvertToRecyclePool.value = true;
  };

  const handleRecycleSubmit = () => {
    return transferMachinePool({
      bk_host_ids: selected.value.map((item) => item.bk_host_id),
      hcm_recycle: true,
      source: 'recycle',
      target: 'recycled',
    });
  };

  const handleDeleteSubmit = () => {
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
    // clearSelection();
    fetchData();
  };

  const handleDeleteRefresh = () => {
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
