<template>
  <BkTableColumn
    field="cluster_name"
    :label="t('集群名称')"
    :min-width="200">
    <template #header>
      <RenderHeadCopy
        :config="[
          {
            field: 'cluster_name',
          },
        ]"
        :has-selected="selectedList.length > 0"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ t('集群名称') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ data }: { data: TendnclusterModel }">
      <TextOverflowLayout>
        {{ data.cluster_name }}
        <template #append>
          <BkPopover v-if="data.temporary_info?.source_cluster">
            <DbIcon
              style="margin-left: 5px; color: #1cab88; cursor: pointer"
              type="clone" />
            <template #content>
              <div class="struct-cluster-source-popover">
                <div class="title">{{ t('构造集群') }}</div>
                <div class="item-row">
                  <div class="label">{{ t('构造源集群') }}：</div>
                  <div class="content">{{ data.temporary_info?.source_cluster }}</div>
                </div>
                <div class="item-row">
                  <div class="label">{{ t('关联单据') }}：</div>
                  <div
                    class="content"
                    style="color: #3a84ff"
                    @click="() => handleGoTicket(data.temporary_info.ticket_id)">
                    {{ data.temporary_info.ticket_id }}
                  </div>
                </div>
              </div>
            </template>
          </BkPopover>
          <DbIcon
            v-bk-tooltips="t('复制集群名称')"
            type="copy"
            @click="() => handleCopyClusterName(data.cluster_name)" />
        </template>
      </TextOverflowLayout>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendnclusterModel from '@services/model/tendbcluster/tendbcluster';

  import DbTable from '@components/db-table/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import RenderHeadCopy from '@views/db-manage/common/render-head-copy/Index.vue';

  import { execCopy } from '@utils';

  import useColumnCopy from './hooks/useColumnCopy';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();
  const router = useRouter();

  const { handleCopySelected, handleCopyAll } = useColumnCopy(props);

  const handleGoTicket = (billId: number) => {
    const route = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: billId,
      },
    });
    window.open(route.href);
  };

  const handleCopyClusterName = (clusterName: string) => {
    execCopy(clusterName);
  };
</script>
