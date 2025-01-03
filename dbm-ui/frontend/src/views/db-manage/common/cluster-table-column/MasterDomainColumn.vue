<template>
  <BkTableColumn
    field="master_domain"
    fixed="left"
    :min-width="280">
    <template #header>
      <RenderHeadCopy
        :config="[
          {
            field: 'master_domain',
            label: t('域名'),
          },
          {
            field: 'masterDomainDisplayName',
            label: t('域名:端口'),
          },
        ]"
        :has-selected="selectedList.length > 0"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ t('主访问入口') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ data }: { data: TendnclusterModel }">
      <TextOverflowLayout>
        <AuthButton
          :action-id="viewActionId"
          :permission="data.permission[viewActionId]"
          :resource="data.id"
          text
          theme="primary"
          @click="handleToDetails(data.id)">
          {{ data.masterDomainDisplayName }}
        </AuthButton>
        <template #append>
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
          <RenderCellCopy
            v-if="data.master_domain"
            :copy-items="[
              {
                value: data.master_domain,
                label: t('域名'),
              },
              {
                value: data.masterDomainDisplayName,
                label: t('域名:端口'),
              },
            ]" />
          <span v-db-console="accessEntryDbConsole">
            <EditEntryConfig
              :id="data.id"
              :biz-id="data.bk_biz_id"
              :permission="data.permission.access_entry_edit"
              :resource="clusterTypeInfos[clusterType].dbType"
              :sort="entrySort"
              @success="{ fetchTableData }">
              <template #prepend="clusterEntry">
                <BkTag
                  v-if="clusterEntry.role === 'master_entry'"
                  size="small"
                  theme="success">
                  {{ t('主') }}
                </BkTag>
                <BkTag
                  v-else
                  size="small"
                  theme="info">
                  {{ t('从') }}
                </BkTag>
              </template>
            </EditEntryConfig>
          </span>
        </template>
      </TextOverflowLayout>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import TendnclusterModel from '@services/model/tendbcluster/tendbcluster';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import EditEntryConfig, { type ClusterEntryInfo } from '@views/db-manage/common/cluster-entry-config/Index.vue';
  import RenderCellCopy from '@views/db-manage/common/render-cell-copy/Index.vue';
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  import useColumnCopy from './hooks/useColumnCopy';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export interface Emits {
    (e: 'go-detail', params: number): void;
    (e: 'refresh'): void;
  }

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const actionIdMap = {
    [ClusterTypes.TENDBCLUSTER]: 'tendbcluster_view',
  } as const;

  const dbConsoleMap = {
    [ClusterTypes.TENDBCLUSTER]: 'tendbCluster.clusterManage.modifyEntryConfiguration',
  } as const;

  const entrySort = (data: ClusterEntryInfo[]) => data.sort((a) => (a.role === 'master_entry' ? -1 : 1));

  const { t } = useI18n();

  const viewActionId = computed(() => actionIdMap[props.clusterType]);

  const accessEntryDbConsole = computed(() => dbConsoleMap[props.clusterType]);

  const { handleCopySelected, handleCopyAll } = useColumnCopy(props);

  const handleToDetails = (id: number) => {
    emits('go-detail', id);
  };

  const fetchTableData = () => {
    emits('refresh');
  };
</script>
