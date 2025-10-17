<template>
  <PrimaryTable
    :data="ticketDetails.details.infos"
    row-key="id">
    <TableColumn
      :min-width="150"
      :title="t('目标Proxy')">
      <template #default="{ row: data }: { row: RowData }">
        {{
          data.old_nodes.origin_proxy?.[0]
            ? `${data.old_nodes.origin_proxy[0].ip}:${data.old_nodes.origin_proxy[0].port}`
            : '--'
        }}
      </template>
    </TableColumn>
    <TableColumn
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
    </TableColumn>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_AUTO">
      <TableColumn
        :min-width="120"
        :title="t('规格')">
        <template #default="{ row: data }: { row: RowData }">
          {{ ticketDetails.details.specs?.[data.resource_spec.target_proxy.spec_id]?.name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
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
      </TableColumn>
    </template>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_MANUAL">
      <TableColumn
        :min-width="120"
        :title="t('新Proxy主机')">
        <template #default="{ row: data }: { row: RowData }">
          {{ data.resource_spec.target_proxy.hosts?.[0]?.ip || '--' }}
        </template>
      </TableColumn>
    </template>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxySwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();
</script>
