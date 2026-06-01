<template>
  <div class="redis-instance-list-page">
    <div class="operation-box">
      <InstanceBatchCopy
        v-db-console="'redis.instanceManage.batchCopy'"
        field="instance_address"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <InstanceBatchCopy
        v-db-console="'redis.instanceManage.batchCopy'"
        class="ml-8"
        field="ip"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <DropdownExportExcel
        v-db-console="'redis.instanceManage.export'"
        class="ml-8"
        export-type="instance"
        :has-selected="isSelected"
        :ids="selectedIdList"
        type="redis" />
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <InstanceTable
      ref="instanceTable"
      :bk-ui-settings="settings"
      :cluster-type="ClusterTypes.REDIS_CLUSTER"
      :data-source="dataSource"
      :filter-value="quickSearchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #instanceAddress>
        <InstanceAddressColumn
          :cluster-type="ClusterTypes.REDIS_CLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </InstanceAddressColumn>
      </template>
      <template #relatedCluster>
        <MasterDomainColumn
          :cluster-type="ClusterTypes.REDIS_CLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </MasterDomainColumn>
      </template>
      <template #ip>
        <IpColumn
          :cluster-type="ClusterTypes.REDIS_CLUSTER"
          :get-table-instance="getTableInstance"
          :is-filter="isSearching"
          :selected-list="selectedList">
        </IpColumn>
      </template>
    </InstanceTable>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import { getRedisInstances } from '@services/source/redis';

  import { useInstanceQuickSearch, useTableSettings } from '@hooks';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import InstanceBatchCopy from '@views/db-manage/common/instance-batch-copy/Index.vue';
  import InstanceTable, {
    InstanceAddressColumn,
    IpColumn,
    MasterDomainColumn,
  } from '@views/db-manage/common/instance-table/Index.vue';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';

  const { t } = useI18n();

  const { isSearching, quickSearchData, quickSearchValue } = useInstanceQuickSearch({
    cluster_type: [
      ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
      ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ClusterTypes.PREDIXY_REDIS_CLUSTER,
    ],
  });
  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.REDIS_INSTANCE_SETTINGS, {
    disabled: ['instance_address'],
  });

  const { handleSelection, isSelected, selectedIdList, selectedList } = useClusterTableSelect<RedisInstanceModel>();

  const instanceTableRef = useTemplateRef('instanceTable');

  const dataSource = (params: ServiceParameters<typeof getRedisInstances>) =>
    getRedisInstances({
      ...params,
      cluster_type: [
        ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
        ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
        ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
        ClusterTypes.PREDIXY_REDIS_CLUSTER,
      ].join(','),
    });

  const getTableInstance = () => instanceTableRef.value;

  const getBatchCopyData = () => {
    return instanceTableRef.value!.getAllData<RedisInstanceModel>();
  };

  const fetchData = () => {
    instanceTableRef.value!.fetchData(quickSearchValue.value);
  };

  const handleQuickSearchChange = () => {
    fetchData();
    // instanceTableRef.value!.clearSelected();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };
</script>

<style lang="less">
  .redis-instance-list-page {
    .operation-box {
      display: flex;
      margin-bottom: 16px;
    }
  }
</style>
