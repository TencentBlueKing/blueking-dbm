<template>
  <InfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <InfoTableColumn
      col-key="origin_proxy"
      :get-copy-value="
        (item: RowData) =>
          item.old_nodes.origin_proxy?.[0]
            ? `${item.old_nodes.origin_proxy[0].ip}:${item.old_nodes.origin_proxy[0].port}`
            : ''
      "
      :min-width="150"
      :title="t('目标Proxy')">
      <template #default="{ row: data }: { row: RowData }">
        {{
          data.old_nodes.origin_proxy?.[0]
            ? `${data.old_nodes.origin_proxy[0].ip}:${data.old_nodes.origin_proxy[0].port}`
            : '--'
        }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="related_clusters"
      :min-width="250"
      :title="t('关联集群')">
      <template #default="{ row: data }: { row: RowData }">
        <template
          v-if="ticketDetails.details.machine_infos?.[data.old_nodes.origin_proxy?.[0].ip]?.related_clusters?.length">
          <p
            v-for="clusterId in ticketDetails.details.machine_infos[data.old_nodes.origin_proxy[0].ip].related_clusters"
            :key="clusterId">
            {{ ticketDetails.details.clusters[clusterId]?.immute_domain || '--' }}
          </p>
        </template>
        <template v-else> -- </template>
      </template>
    </InfoTableColumn>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_AUTO">
      <InfoTableColumn
        col-key="spec_id"
        :min-width="120"
        :title="t('规格')">
        <template #default="{ row: data }: { row: RowData }">
          {{ ticketDetails.details.specs?.[data.resource_spec.target_proxy.spec_id]?.name || '--' }}
        </template>
      </InfoTableColumn>
      <InfoTableColumn
        col-key="label_names"
        :min-width="200"
        :title="t('资源标签')">
        <template #default="{ row: data }: { row: RowData }">
          <template v-if="data.resource_spec.target_proxy?.label_names?.length">
            <BkTag
              v-for="item in data.resource_spec.target_proxy.label_names"
              :key="item">
              {{ item }}
            </BkTag>
          </template>
          <BkTag
            v-else
            theme="success">
            {{ t('通用无标签') }}
          </BkTag>
        </template>
      </InfoTableColumn>
    </template>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_MANUAL">
      <InfoTableColumn
        col-key="target_proxy"
        :min-width="120"
        :title="t('新Proxy主机')">
        <template #default="{ row: data }: { row: RowData }">
          {{ data.resource_spec.target_proxy.hosts?.[0]?.ip || '--' }}
        </template>
      </InfoTableColumn>
    </template>
  </InfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  import InfoTable, { InfoTableColumn } from '../../../../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxySwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();
</script>
