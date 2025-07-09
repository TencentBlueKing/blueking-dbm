<template>
  <TableColumn
    class-name="cluster-table-cluster-name-column"
    col-key="cluster_name"
    :min-width="200"
    :title="t('集群名称')">
    <template #title>
      <RenderHeadCopy
        :config="[
          {
            field: 'cluster_name',
          },
        ]"
        :has-selected="selectedList.length > 0"
        :is-filter="isFilter"
        @handle-copy-all="handleCopyAll"
        @handle-copy-selected="handleCopySelected">
        {{ t('集群名称') }}
      </RenderHeadCopy>
    </template>
    <template #default="{ row }: { row: TendnclusterModel }">
      <div @mouseenter="handleToolsShow">
        <TextOverflowLayout>
          {{ row.cluster_name }}
          <template
            v-if="isToolsShow"
            #append>
            <BkPopover v-if="row.temporary_info?.source_cluster">
              <DbIcon
                style="margin-left: 5px; color: #1cab88; cursor: pointer"
                type="clone" />
              <template #content>
                <div class="struct-cluster-source-popover">
                  <div class="title">{{ t('构造集群') }}</div>
                  <div class="item-row">
                    <div class="label">{{ t('构造源集群') }}：</div>
                    <div class="content">{{ row.temporary_info?.source_cluster }}</div>
                  </div>
                  <div class="item-row">
                    <div class="label">{{ t('关联单据') }}：</div>
                    <div
                      class="content"
                      style="color: #3a84ff"
                      @click="() => handleGoTicket(row.temporary_info.ticket_id)">
                      {{ row.temporary_info.ticket_id }}
                    </div>
                  </div>
                </div>
              </template>
            </BkPopover>
            <DbIcon
              v-bk-tooltips="t('复制集群名称')"
              type="copy"
              @click="handleCopyClusterName(row.cluster_name)" />
          </template>
        </TextOverflowLayout>
      </div>
    </template>
  </TableColumn>
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
    // eslint-disable-next-line vue/no-unused-properties
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
    isFilter: boolean;
    selectedList: ClusterModel<clusterType>[];
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();
  const router = useRouter();

  const isToolsShow = ref(false);

  const { handleCopyAll, handleCopySelected } = useColumnCopy(props);

  const handleToolsShow = () => {
    setTimeout(() => {
      isToolsShow.value = true;
    }, 1000);
  };

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
    execCopy(clusterName, t('复制成功，共n条', { n: 1 }));
  };
</script>
<style lang="less">
  .cluster-table-cluster-name-column {
    &:hover {
      [class*='db-icon'] {
        display: block;
      }
    }

    [class*='db-icon'] {
      display: none;
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
