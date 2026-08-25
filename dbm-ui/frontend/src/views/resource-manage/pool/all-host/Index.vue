<template>
  <div class="all-host-container">
    <BkAlert
      class="mb-12"
      closable
      :title="t('外部主机导入资源池后将在此被记录。直至在待回收池完成删除操作，相关记录才会被删除')" />
    <div class="operation-wrapper">
      <BkDropdown
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
        col-key="pool"
        :filter="columnFilter?.pool"
        :title="t('所属池')"
        :width="130">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.poolDispaly }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="city"
        :filter="columnFilter?.city"
        :title="t('地域')">
      </TableColumn>
      <TableColumn
        col-key="sub_zone"
        :filter="columnFilter?.sub_zone"
        :title="t('园区')">
      </TableColumn>
      <TableColumn
        col-key="rack_id"
        :filter="columnFilter?.rack_id"
        :title="t('机架')">
      </TableColumn>
      <TableColumn
        col-key="os_name"
        :filter="columnFilter?.os_name"
        :title="t('操作系统')"
        :width="180">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          {{ row.os_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="device_class"
        :filter="columnFilter?.device_class"
        :title="t('机型')">
      </TableColumn>
      <TableColumn
        col-key="bk_cpu"
        :title="t('CPU (核)')"
        :width="80">
      </TableColumn>
      <TableColumn
        col-key="bkMemText"
        :min-width="90"
        :title="t('内存（G）')" />
      <TableColumn
        col-key="bk_disk"
        :title="t('磁盘 (G)')">
      </TableColumn>
      <TableColumn
        col-key="row-operation"
        :title="t('操作')"
        :width="100">
        <template #default="{ row }: { row: FaultOrRecycleMachineModel }">
          <BkButton
            text
            theme="primary"
            @click="handleShowRecord(row)">
            {{ t('操作记录') }}
          </BkButton>
        </template>
      </TableColumn>
    </DbTable>
    <Record
      v-if="currentRow"
      v-model="isRecordShow"
      :data="currentRow" />
  </div>
</template>

<script setup lang="tsx">
  import BkButton from 'bkui-vue/lib/button';
  import { useI18n } from 'vue-i18n';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { getMachinePool } from '@services/source/dbdirty';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { useColumnFilter } from '@views/resource-manage/common/hooks/useColumnFilter';
  import { useQuickSearch } from '@views/resource-manage/common/hooks/useQuickSearch';

  import { execCopy, messageWarn } from '@utils';

  import Record from './components/Record.vue';

  const { t } = useI18n();
  const { isSearching, quickSearchData, quickSearchValue } = useQuickSearch();
  const { data: columnFilter } = useColumnFilter();

  const tableRef = useTemplateRef('tableRef');

  const isRecordShow = ref(false);

  const selected = shallowRef<FaultOrRecycleMachineModel[]>([]);
  const currentRow = shallowRef<FaultOrRecycleMachineModel>();

  const dataSource = (params: ServiceParameters<typeof getMachinePool>) =>
    getMachinePool({
      ...params,
      bk_biz_id: undefined,
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

  const handleSelection = (key: any, list: Record<number, FaultOrRecycleMachineModel>[]) => {
    selected.value = list as unknown as FaultOrRecycleMachineModel[];
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

  const handleShowRecord = (data: FaultOrRecycleMachineModel) => {
    isRecordShow.value = true;
    currentRow.value = data;
  };
</script>

<style lang="less" scoped>
  .all-host-container {
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
