<template>
  <div class="cluster-detail-host-list-box">
    <div class="mb-16 action-box">
      <BkButton
        v-bk-tooltips="{
          content: t('请选择主机'),
          disabled: selectedHostList.length > 0,
        }"
        :disabled="selectedHostList.length < 1"
        style="width: 105px"
        @click="handleSelectedHostIp">
        {{ t('复制已选 IP') }}
      </BkButton>
      <BkButton
        class="ml-8"
        style="width: 105px"
        @click="handleNotAliveHostIp">
        {{ t('复制异常 IP') }}
      </BkButton>
      <BkButton
        class="ml-8 mr-20"
        style="width: 105px"
        @click="handleAllHostIp">
        {{ t('复制所有 IP') }}
      </BkButton>
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        :placeholder="t('请输入或选择条件搜索')"
        style="flex: 1; max-width: 560px; margin-left: auto" />
    </div>
    <DbTable
      ref="hostTableRef"
      :data-source="dataSource"
      :filter-value="quickSearchValue"
      row-key="bk_host_id"
      selectable
      @filter-change="handleFilterChange"
      @selection="handleSelectChange">
      <HostListFieldColumn
        :cluster-id="clusterId"
        :cluster-type="clusterType" />
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useHostQuickSearch } from '@hooks';

  import DbTable from '@components/db-table/IndexNew.vue';

  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { useCopyMachineIp } from '../hooks';
  import HostListFieldColumn from '../HostListFieldColumn.vue';

  interface Props {
    clusterId: number;
    clusterType: Parameters<typeof useClusterMachineList>[0];
  }
  const props = defineProps<Props>();

  type IData = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number];

  const { t } = useI18n();

  const { copyAllIp, copyNotAliveIp } = useCopyMachineIp();
  const requestHandler = useClusterMachineList(props.clusterType);

  const hostTableRef = ref<InstanceType<typeof DbTable>>();
  const { quickSearchData, quickSearchValue } = useHostQuickSearch(props.clusterType, {
    clusterId: props.clusterId,
    serviceHandler: () => {
      fetchData();
    },
  });

  const dataSource = (params: ServiceParameters<typeof requestHandler>) =>
    requestHandler({
      cluster_ids: `${props.clusterId}`,
      ...params,
    });

  const selectedHostList = shallowRef<IData[]>([]);

  const fetchData = () => {
    hostTableRef?.value?.fetchData({ ...quickSearchValue.value });
  };

  const handleSelectChange = (_key: string[], list: IData[]) => {
    selectedHostList.value = list;
  };

  const handleSelectedHostIp = () => {
    copyAllIp(selectedHostList.value);
  };

  const handleNotAliveHostIp = () => {
    copyNotAliveIp(hostTableRef.value!.getData() || []);
  };

  const handleAllHostIp = () => {
    copyAllIp(hostTableRef.value!.getData() || []);
  };

  const handleFilterChange = (filterValue: Record<string, any>) => {
    quickSearchValue.value = filterValue;
  };
</script>
<style lang="less">
  .cluster-detail-host-list-box {
    height: 100%;
    padding: 18px 0;

    .action-box {
      display: flex;
    }
  }
</style>
