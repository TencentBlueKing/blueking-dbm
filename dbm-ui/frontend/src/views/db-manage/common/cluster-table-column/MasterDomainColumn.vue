<template>
  <BkTableColumn
    class-name="cluster-table-master-domain-column"
    :field="field"
    fixed="left"
    :label="label"
    :min-width="columnMinWidth"
    visiable>
    <template #header>
      <RenderHeadCopy
        :config="[
          {
            field: 'masterDomain',
            label: t('域名'),
          },
          {
            field: 'masterDomainDisplayName',
            label: t('域名:端口'),
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ label }}
      </RenderHeadCopy>
    </template>
    <template #default="{ data }: { data: IRowData }">
      <div @mouseenter="handleToolsShow">
        <TextOverflowLayout>
          <AuthButton
            :action-id="viewActionId"
            :permission="Boolean(_.get(data.permission, viewActionId))"
            :resource="data.id"
            text
            theme="primary"
            @click="handleToDetails(data.id)">
            {{ data.masterDomainDisplayName }}
          </AuthButton>
          <template #append>
            <slot
              name="append"
              v-bind="{ data: data }" />
            <RenderOperationTag
              v-for="(item, index) in data.operationTagTips"
              :key="index"
              class="cluster-tag ml-4"
              :data="item" />
            <BkTag
              v-if="data.isOffline && !data.isStarting"
              class="ml-4"
              size="small">
              {{ t('已禁用') }}
            </BkTag>
            <BkTag
              v-if="data.isNew"
              class="ml-4"
              size="small"
              theme="success">
              NEW
            </BkTag>
            <template v-if="isToolsShow">
              <PopoverCopy>
                <div @click="handleCopy(data.masterDomain)">{{ t('复制域名') }}</div>
                <div @click="handleCopy(data.masterDomainDisplayName)">{{ t('复制域名:端口') }}</div>
              </PopoverCopy>
              <span v-db-console="accessEntryDbConsole">
                <EditEntryConfig
                  :id="data.id"
                  :biz-id="data.bk_biz_id"
                  :permission="Boolean(data.permission.access_entry_edit)"
                  :resource="dbType || clusterTypeInfos[clusterType].dbType"
                  @success="handleRefresh" />
              </span>
            </template>
          </template>
        </TextOverflowLayout>
      </div>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { clusterTypeInfos, ClusterTypes, DBTypes } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import PopoverCopy from '@components/popover-copy/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import EditEntryConfig from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  import { execCopy } from '@utils';

  import useColumnCopy from './hooks/useColumnCopy';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    label: string;
    field: string;
    clusterType: clusterType;
    dbType?: DBTypes;
    selectedList: ClusterModel<clusterType>[];
    isFilter: boolean;
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export interface Emits {
    (e: 'go-detail', params: number): void;
    (e: 'refresh'): void;
  }

  export interface Slots<T extends ISupportClusterType> {
    append?: (params: { data: ClusterModel<T> }) => VNode;
  }

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();
  defineSlots<Slots<T>>();

  const viewActionIdMap: Record<ISupportClusterType, string> = {
    [ClusterTypes.TENDBCLUSTER]: 'tendbcluster_view',
    [ClusterTypes.DORIS]: 'doris_view',
    [ClusterTypes.ES]: 'es_view',
    [ClusterTypes.HDFS]: 'hdfs_view',
    [ClusterTypes.TENDBHA]: 'mysql_view',
    [ClusterTypes.TENDBSINGLE]: 'mysql_view',
    [ClusterTypes.PULSAR]: 'pulsar_view',
    [ClusterTypes.REDIS]: 'redis_view',
    [ClusterTypes.REDIS_INSTANCE]: 'redis_view',
    [ClusterTypes.RIAK]: 'riak_view',
    [ClusterTypes.KAFKA]: 'kafka_view',
    [ClusterTypes.SQLSERVER_HA]: 'sqlserver_view',
    [ClusterTypes.SQLSERVER_SINGLE]: 'sqlserver_view',
    [ClusterTypes.MONGO_REPLICA_SET]: 'mongodb_view',
    [ClusterTypes.MONGO_SHARED_CLUSTER]: 'mongodb_view',
  };

  const dbConsoleMap: Record<ISupportClusterType, string> = {
    [ClusterTypes.TENDBCLUSTER]: 'tendbCluster.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.DORIS]: 'doris.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.ES]: 'es.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.HDFS]: 'hdfs.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.TENDBHA]: 'mysql.haClusterList.modifyEntryConfiguration',
    [ClusterTypes.TENDBSINGLE]: 'mysql.singleClusterList.modifyEntryConfiguration',
    [ClusterTypes.PULSAR]: 'pulsar.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.REDIS]: 'redis.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.REDIS_INSTANCE]: 'redis.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.RIAK]: 'riak.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.KAFKA]: 'kafka.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.SQLSERVER_HA]: 'sqlserver.haClusterList.modifyEntryConfiguration',
    [ClusterTypes.SQLSERVER_SINGLE]: 'sqlserver.singleClusterList.modifyEntryConfiguration',
    [ClusterTypes.MONGO_REPLICA_SET]: 'mongodb.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.MONGO_SHARED_CLUSTER]: 'mongodb.clusterManage.modifyEntryConfiguration',
  };

  const { t } = useI18n();

  const columnMinWidth = window.innerWidth < 1366 ? 180 : 280;

  const isToolsShow = ref(false);
  const viewActionId = computed(() => viewActionIdMap[props.clusterType]);

  const accessEntryDbConsole = computed(() => dbConsoleMap[props.clusterType]);

  const { handleCopySelected, handleCopyAll } = useColumnCopy(props);

  const handleToolsShow = () => {
    setTimeout(() => {
      isToolsShow.value = true;
    }, 1000);
  };

  const handleCopy = (data: string) => {
    execCopy(data, t('复制成功，共n条', { n: 1 }));
  };

  const handleToDetails = (id: number) => {
    emits('go-detail', id);
  };

  const handleRefresh = () => {
    emits('refresh');
  };
</script>
<style lang="less">
  .cluster-table-master-domain-column {
    &:hover {
      [class*=' db-icon'] {
        display: inline !important;
      }
    }

    [class*=' db-icon'] {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
