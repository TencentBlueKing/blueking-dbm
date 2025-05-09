<template>
  <div
    v-for="slaveItem in data.slice(0, renderCount)"
    :key="slaveItem.entry"
    class="mb-4">
    {{ slaveItem.entry }}:{{ slaveItem.port }}
  </div>
  <span v-if="data.length < 1">--</span>
  <div v-if="data.length > renderCount">
    <span>... </span>
    <BkPopover
      placement="top"
      theme="light">
      <BkTag>
        <I18nT keypath="共n个">{{ data.length }}</I18nT>
      </BkTag>
      <template #content>
        <div style="max-height: 280px; overflow: scroll">
          <div
            v-for="slaveItem in data"
            :key="slaveItem.entry"
            style="line-height: 20px">
            {{ slaveItem.entry }}:{{ slaveItem.port }}
          </div>
        </div>
      </template>
    </BkPopover>
  </div>
</template>

<script setup lang="ts" generic="T extends ISupportClusterType">
  import TendbhaModel from '@services/model/mysql/tendbha';
  import RedisModel from '@services/model/redis/redis';
  import SqlserverHaModel from '@services/model/sqlserver/sqlserver-ha';
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import { ClusterTypes } from '@common/const';

  export type ISupportClusterType =
    | ClusterTypes.TENDBCLUSTER
    | ClusterTypes.TENDBHA
    | ClusterTypes.REDIS_INSTANCE
    | ClusterTypes.SQLSERVER_HA;

  export interface ClusterTypeRelateClusterModel {
    [ClusterTypes.REDIS_INSTANCE]: RedisModel;
    [ClusterTypes.SQLSERVER_HA]: SqlserverHaModel;
    [ClusterTypes.TENDBCLUSTER]: TendbClusterModel;
    [ClusterTypes.TENDBHA]: TendbhaModel;
  }

  export type SlaveEntryList<T extends keyof ClusterTypeRelateClusterModel> =
    ClusterTypeRelateClusterModel[T]['slaveEntryList'];

  export interface Props<clusterType extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: clusterType;
    data: SlaveEntryList<clusterType>;
  }

  defineProps<Props<T>>();

  const renderCount = 6;
</script>
