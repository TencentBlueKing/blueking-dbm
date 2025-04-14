<template>
  <div class="all-host-container">
    <BkAlert
      class="mb-12"
      closable
      :title="t('有导入资源池的主机都会记录在这里，直到在待回收池执行回收操作')" />
    <div class="operation-wrapper">
      <BkDropdown>
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
      :data-source="dataSource"
      primary-key="bk_host_id"
      releate-url-query
      selectable
      :show-settings="false"
      @clear-search="handleClearSearch"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection">
      <BkTableColumn
        field="ip"
        fixed="left"
        label="IP"
        :width="150">
      </BkTableColumn>
      <BkTableColumn
        field="poolDispaly"
        :label="t('所属池')"
        :width="130">
      </BkTableColumn>
      <BkTableColumn
        field="city"
        :label="t('地域')">
      </BkTableColumn>
      <BkTableColumn
        field="sub_zone"
        :label="t('园区')">
      </BkTableColumn>
      <BkTableColumn
        field="rack_id"
        :label="t('机架')">
      </BkTableColumn>
      <BkTableColumn
        field="os_name"
        :label="t('操作系统')"
        show-overflow="tooltip"
        :width="180">
      </BkTableColumn>
      <BkTableColumn
        field="device_class"
        :label="t('机型')">
      </BkTableColumn>
      <BkTableColumn
        field="bk_cpu"
        :label="t('CPU (核)')"
        :width="80">
      </BkTableColumn>
      <BkTableColumn
        field="bkMemText"
        :label="t('内存')"
        show-overflow
        :width="80">
        <template #default="{ data }: { data: FaultOrRecycleMachineModel }">
          {{ data.bkMemText || '0 M' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="bk_disk"
        :label="t('磁盘 (G)')">
      </BkTableColumn>
      <BkTableColumn
        field=""
        :label="t('操作')"
        :width="100">
        <template #default="{ data }: { data: FaultOrRecycleMachineModel }">
          <BkButton
            text
            theme="primary"
            @click="handleRecord(data)">
            {{ t('操作记录') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </DbTable>
    <Record
      v-if="currentRow"
      v-model="isRecordShow"
      :data="currentRow" />
  </div>
</template>

<script setup lang="tsx">
  import BkButton from 'bkui-vue/lib/button';
  import type { ISearchItem } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { getMachinePool } from '@services/source/dbdirty';
  import { fetchDeviceClass } from '@services/source/dbresourceResource';

  import { useLinkQueryColumnSerach } from '@hooks';

  import { execCopy, getMenuListSearch, getSearchSelectorParams, messageWarn } from '@utils';

  import Record from './components/Record.vue';

  const { t } = useI18n();

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

  const isRecordShow = ref(false);

  const selected = shallowRef<FaultOrRecycleMachineModel[]>([]);
  const currentRow = shallowRef<FaultOrRecycleMachineModel>();

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

  const dataSource = (params: ServiceParameters<typeof getMachinePool>) =>
    getMachinePool({
      ...params,
      bk_biz_id: undefined,
    });

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData(searchParams);
  };

  const handleSelection = (key: any, list: Record<number, FaultOrRecycleMachineModel>[]) => {
    selected.value = list as unknown as FaultOrRecycleMachineModel[];
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

  const handleRecord = (data: FaultOrRecycleMachineModel) => {
    isRecordShow.value = true;
    currentRow.value = data;
  };

  onMounted(() => {
    fetchData();
  });
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
