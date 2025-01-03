<template>
  <BkTableColumn
    field="slave_domain"
    :label="t('从访问入口')"
    :min-width="200">
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
    <template #default="{ data }: { data: TendnclusterModel }">
      <TextOverflowLayout>
        {{ data.slaveDomainDisplayName }}
        <template #append>
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
              :sort="entrySort"
              @success="fetchTableData">
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
  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import { execCopy } from '@utils';

  import useColumnCopy from './hooks/useColumnCopy';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export interface Emits {
    (e: 'refresh'): void;
  }

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const dbConsoleMap = {
    [ClusterTypes.TENDBCLUSTER]: 'tendbCluster.clusterManage.modifyEntryConfiguration',
  } as const;

  const entrySort = (data: ClusterEntryInfo[]) => data.sort((a) => (a.role === 'master_entry' ? -1 : 1));

  const { t } = useI18n();

  const accessEntryDbConsole = computed(() => dbConsoleMap[props.clusterType]);

  const { handleCopySelected, handleCopyAll } = useColumnCopy(props);

  const handleCopySlaveDomain = (clusterName: string) => {
    execCopy(clusterName);
  };

  const fetchTableData = () => {
    emits('refresh');
  };
</script>
