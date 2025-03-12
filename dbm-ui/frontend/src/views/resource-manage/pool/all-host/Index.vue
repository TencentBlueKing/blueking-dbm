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
            <BkDropdownItem @click="handleCopyAllHost">{{ t('所有 IP') }}</BkDropdownItem>
            <BkDropdownItem @click="handleCopySelectHost">{{ t('已选 IP') }}</BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <HostSearchSelect
        v-model="searchValue"
        class="pool-search-selector"
        @search="fetchData" />
    </div>
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      primary-key="bk_host_id"
      releate-url-query
      selectable
      :show-settings="false"
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
        :label="t('CPU (核)')">
      </BkTableColumn>
      <BkTableColumn
        field="bk_mem"
        :label="t('内存')"
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
      :ip="currentRow.ip" />
  </div>
</template>

<script setup lang="tsx">
  import BkButton from 'bkui-vue/lib/button';
  import { useI18n } from 'vue-i18n';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';
  import { getMachinePool } from '@services/source/dbdirty';

  import HostSearchSelect from '@views/resource-manage/common/components/host-search-select/Index.vue';

  import { execCopy, getSearchSelectorParams } from '@utils';

  import Record from './components/Record.vue';

  const { t } = useI18n();

  const tableRef = useTemplateRef('tableRef');

  const searchValue = ref([]);
  const isRecordShow = ref(false);

  const selected = shallowRef<FaultOrRecycleMachineModel[]>([]);
  const currentRow = shallowRef<FaultOrRecycleMachineModel>();

  const dataSource = (params: ServiceParameters<typeof getMachinePool>) =>
    getMachinePool({
      ...params,
      bk_biz_id: undefined,
    });

  watch(searchValue, () => {
    fetchData();
  });

  const fetchData = () => {
    const searchParams = getSearchSelectorParams(searchValue.value);
    tableRef.value?.fetchData(searchParams);
  };

  const handleSelection = (key: any, list: Record<number, FaultOrRecycleMachineModel>[]) => {
    selected.value = list as unknown as FaultOrRecycleMachineModel[];
  };

  const handleCopyAllHost = () => {
    getMachinePool({
      limit: -1,
      offset: 0,
    }).then((data) => {
      const ipList = data.results.map((item) => item.ip);
      execCopy(ipList.join('\n'), `${t('复制成功n个IP', { n: ipList.length })}\n`);
    });
  };

  const handleCopySelectHost = () => {
    const ipList = selected.value.map((item) => item.ip);
    execCopy(ipList.join('\n'), `${t('复制成功n个IP', { n: ipList.length })}\n`);
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
