<template>
  <TableColumn
    class-name="cluster-table-cluster-name-column"
    col-key="name"
    :filter="columnFilter?.['name']"
    :min-width="200"
    :title="t('集群名称')">
    <template #default="{ row }: { row: TendnclusterModel }">
      <div @mouseenter="handleToolsShow">
        <TextOverflowLayout>
          {{ row.cluster_name }}
          <template
            v-if="isToolsShow"
            #append>
            <BkPopover v-if="row.temporary_info?.source_cluster">
              <span role="table-cell-operation">
                <DbIcon
                  role="table-cell-operation"
                  style="color: #1cab88; cursor: pointer"
                  type="clone" />
              </span>
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
            <span role="table-cell-operation">
              <DbIcon
                v-bk-tooltips="t('复制集群名称')"
                type="copy"
                @click="handleCopyClusterName(row.cluster_name)" />
            </span>
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

  import { useClusterColumnFilter } from '@hooks';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  import type { ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    clusterType: clusterType;
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();
  const router = useRouter();

  const isToolsShow = ref(false);

  const { data: columnFilter } = useClusterColumnFilter({
    cluster_type: props.clusterType,
  });

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
