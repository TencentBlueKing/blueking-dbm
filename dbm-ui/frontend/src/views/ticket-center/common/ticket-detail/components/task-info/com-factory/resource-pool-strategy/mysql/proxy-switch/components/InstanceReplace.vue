<template>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('目标Proxy')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{
          data.old_nodes.origin_proxy?.[0]
            ? `${data.old_nodes.origin_proxy[0].ip}:${data.old_nodes.origin_proxy[0].port}`
            : '--'
        }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('关联集群')"
      :min-width="300">
      <template #default="{ data }: { data: RowData }">
        <template
          v-if="ticketDetails.details.machine_infos[data.old_nodes.origin_proxy[0].ip]?.related_clusters?.length">
          <p
            v-for="item in ticketDetails.details.machine_infos[data.old_nodes.origin_proxy[0].ip].related_clusters"
            :key="item.immute_domain">
            {{ item.immute_domain }}
          </p>
        </template>
        <template
          v-else-if="relatedCluster[`${data.old_nodes.origin_proxy[0].ip}:${data.old_nodes.origin_proxy[0].port}`]">
          {{ relatedCluster[`${data.old_nodes.origin_proxy[0].ip}:${data.old_nodes.origin_proxy[0].port}`] }}
        </template>
        <template v-else> -- </template>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('新Proxy主机')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.resource_spec.target_proxy.hosts?.[0] ? data.resource_spec.target_proxy.hosts[0].ip : '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { checkInstance } from '@services/source/dbbase';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxySwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  const relatedCluster = reactive<Record<string, string>>({});

  useRequest(checkInstance, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        instance_addresses: props.ticketDetails.details.infos.map((item) => {
          const { ip, port } = item.old_nodes.origin_proxy[0];
          return `${ip}:${port}`;
        }),
      },
    ],
    onSuccess: (data) => {
      data.forEach((item) => {
        Object.assign(relatedCluster, {
          [item.instance_address]: item.master_domain,
        });
      });
    },
  });
</script>
