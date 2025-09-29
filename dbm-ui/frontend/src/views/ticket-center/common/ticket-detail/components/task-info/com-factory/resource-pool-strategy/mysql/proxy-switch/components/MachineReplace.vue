<template>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('目标Proxy')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.proxy?.[0]?.ip || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('关联集群')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId">
          <p>
            {{ ticketDetails.details.clusters[clusterId].immute_domain }}
          </p>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标规格')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.specs?.[data.resource_spec.target_proxy.spec_id]?.name || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('资源标签')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
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
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxySwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();
</script>
