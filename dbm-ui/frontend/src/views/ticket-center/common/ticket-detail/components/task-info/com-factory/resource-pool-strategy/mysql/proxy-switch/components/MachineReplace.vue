<template>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('目标Proxy')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.origin_proxy?.[0]?.ip || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('关联实例')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        <template
          v-if="ticketDetails.details.machine_infos?.[data.old_nodes.origin_proxy?.[0]?.ip]?.related_instances?.length">
          <p
            v-for="item in ticketDetails.details.machine_infos[data.old_nodes.origin_proxy?.[0]?.ip].related_instances"
            :key="item.instance">
            {{ item.instance }}
          </p>
        </template>
        <template v-else> -- </template>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('关联集群')"
      :min-width="300">
      <template #default="{ data }: { data: RowData }">
        <template
          v-if="ticketDetails.details.machine_infos?.[data.old_nodes.origin_proxy?.[0]?.ip]?.related_clusters?.length">
          <p
            v-for="clusterId in ticketDetails.details.machine_infos[data.old_nodes.origin_proxy?.[0]?.ip]
              .related_clusters"
            :key="clusterId">
            {{ ticketDetails.details.clusters[clusterId]?.immute_domain || '--' }}
          </p>
        </template>
        <template v-else> -- </template>
      </template>
    </BkTableColumn>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_AUTO">
      <BkTableColumn
        :label="t('规格')"
        :min-width="120">
        <template #default="{ data }: { data: RowData }">
          {{ ticketDetails.details.specs?.[data.resource_spec.target_proxy.spec_id]?.name || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('资源标签')"
        :min-width="200">
        <template #default="{ data }: { data: RowData }">
          <BkTag
            v-for="item in data.resource_spec.target_proxy.label_names"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
      </BkTableColumn>
      <BkTableColumn
        :label="t('可用资源')"
        :min-width="120">
        <template #default="{ data }: { data: RowData }">
          <BkButton
            text
            theme="primary"
            @click="() => handleClick(data)">
            {{ t('资源预览') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </template>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_MANUAL">
      <BkTableColumn
        :label="t('新Proxy主机')"
        :min-width="120">
        <template #default="{ data }: { data: RowData }">
          {{ data.resource_spec.target_proxy.hosts?.[0]?.ip || '--' }}
        </template>
      </BkTableColumn>
    </template>
  </BkTable>
  <ResourcePreview
    v-model:is-show="showSlider"
    :params="params" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  import { DBTypes } from '@common/const';

  import ResourcePreview from '@views/db-manage/common/toolbox-field/column/available-resource-column/components/ResourcePreview.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxySwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();

  const showSlider = ref(false);
  const params = ref<{
    for_bizs: number[];
    labels: string;
    resource_types: string[];
    spec_id: number;
  }>();

  const handleClick = (data: RowData) => {
    showSlider.value = true;
    params.value = {
      for_bizs: [window.PROJECT_CONFIG.BIZ_ID, 0],
      labels: data.resource_spec.target_proxy.labels.join(','),
      resource_types: [DBTypes.MYSQL, 'PUBLIC'],
      spec_id: data.resource_spec.target_proxy.spec_id,
    };
  };
</script>
