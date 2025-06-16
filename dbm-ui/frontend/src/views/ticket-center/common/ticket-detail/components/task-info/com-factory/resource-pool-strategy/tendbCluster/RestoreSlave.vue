<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('目标从库主机')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.old_slave?.[0]?.ip || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('从库主机关联实例')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        <template
          v-if="ticketDetails.details.machine_infos?.[data.old_nodes.old_slave?.[0]?.ip]?.related_instances?.length">
          <p
            v-for="item in ticketDetails.details.machine_infos[data.old_nodes.old_slave?.[0]?.ip].related_instances"
            :key="item.instance">
            {{ item.instance }}
          </p>
        </template>
        <template v-else> -- </template>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('同机关联集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        <template
          v-if="ticketDetails.details.machine_infos?.[data.old_nodes.old_slave?.[0]?.ip]?.related_clusters?.length">
          <p
            v-for="clusterId in ticketDetails.details.machine_infos[data.old_nodes.old_slave[0].ip].related_clusters"
            :key="clusterId">
            {{ ticketDetails.details.clusters[clusterId]?.immute_domain || '--' }}
          </p>
        </template>
        <template v-else> -- </template>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('机器规格')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{
          ticketDetails.details.specs?.[data.resource_spec.new_slave.spec_id]?.name ||
          ticketDetails.details.machine_infos?.[data.old_nodes.old_slave?.[0]?.ip]?.spec_config?.name ||
          '--'
        }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('资源标签')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.resource_spec.new_slave.label_values"
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
  </BkTable>
  <InfoList>
    <InfoItem :label="t('备份源')">
      {{ ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
    </InfoItem>
  </InfoList>
  <ResourcePreview
    v-model:is-show="showSlider"
    :params="params" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { DBTypes, TicketTypes } from '@common/const';

  import ResourcePreview from '@views/db-manage/common/toolbox-field/column/available-resource-column/components/ResourcePreview.vue';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.RestoreSlave>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_RESTORE_SLAVE,
    inheritAttrs: false,
  });

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
      labels: data.resource_spec.new_slave.labels.join(','),
      resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
      spec_id: data.resource_spec.new_slave.spec_id,
    };
  };
</script>
