<template>
  <BkTableColumn
    field="slave_domain"
    :label="t('从访问入口')"
    :min-width="280">
    <template #header>
      <RenderHeadCopy
        :config="[
          {
            field: 'slave_domain',
            label: t('域名'),
          },
          {
            field: 'slaveDomainDisplayName',
            label: t('域名:端口'),
          },
        ]"
        :has-selected="selectedList.length > 0"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ t('从访问入口') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ data }: { data: IRowData }">
      <div
        v-if="data.slave_domain"
        style="padding: 6px 0">
        <TextOverflowLayout
          v-for="(slaveItem, index) in data.slaveList.slice(0, renderCount)"
          :key="slaveItem.instance"
          style="line-height: 26px">
          {{ data.slave_domain }}:{{ slaveItem.port }}
          <template
            v-if="index === 0"
            #append>
            <DbIcon
              v-if="data.slave_domain"
              v-bk-tooltips="t('复制从访问入口')"
              type="copy"
              @click="() => handleCopySlaveDomain(data.slaveDomainDisplayName)" />
            <span v-db-console="accessEntryDbConsole">
              <EditEntryConfig
                :id="data.id"
                :biz-id="data.bk_biz_id"
                :permission="data.permission.access_entry_edit"
                :resource="clusterTypeInfos[clusterType].dbType"
                @success="fetchTableData">
              </EditEntryConfig>
            </span>
          </template>
        </TextOverflowLayout>
      </div>
      <span v-if="!data.slave_domain">--</span>
      <div v-if="data.slaveList.length > renderCount">
        <span>... </span>
        <BkPopover
          placement="top"
          theme="light">
          <BkTag>
            <I18nT keypath="共n个">{{ data.slaveList.length }}</I18nT>
          </BkTag>
          <template #content>
            <div
              v-for="slaveItem in data.slaveList"
              :key="slaveItem.instance"
              style="line-height: 20px">
              {{ data.slave_domain }}:{{ slaveItem.port }}
            </div>
          </template>
        </BkPopover>
      </div>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import EditEntryConfig from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import { execCopy } from '@utils';

  import useColumnCopy from './hooks/useColumnCopy';
  import type { ClusterModel } from './types';

  export type ISupportClusterType =
    | ClusterTypes.TENDBCLUSTER
    | ClusterTypes.TENDBHA
    | ClusterTypes.REDIS_INSTANCE
    | ClusterTypes.SQLSERVER_HA;

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export interface Emits {
    (e: 'refresh'): void;
  }

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const dbConsoleMap: Record<ISupportClusterType, string> = {
    [ClusterTypes.TENDBCLUSTER]: 'tendbCluster.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.TENDBHA]: 'mysql.haClusterList.modifyEntryConfiguration',
    [ClusterTypes.REDIS_INSTANCE]: 'redis.clusterManage.modifyEntryConfiguration',
    [ClusterTypes.SQLSERVER_HA]: 'sqlserver.haClusterList.modifyEntryConfiguration',
  };

  const { t } = useI18n();

  const renderCount = 1;
  const accessEntryDbConsole = computed(() => dbConsoleMap[props.clusterType]);

  const { handleCopySelected, handleCopyAll } = useColumnCopy(props);

  const handleCopySlaveDomain = (clusterName: string) => {
    execCopy(clusterName);
  };

  const fetchTableData = () => {
    emits('refresh');
  };
</script>
