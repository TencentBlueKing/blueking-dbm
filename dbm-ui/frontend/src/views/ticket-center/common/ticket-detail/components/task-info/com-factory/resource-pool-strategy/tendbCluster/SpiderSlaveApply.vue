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
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('规格')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.specs?.[data.resource_spec.spider_slave_ip_list.spec_id]?.name || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('部署台数')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        {{ data.resource_spec.spider_slave_ip_list.count }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('资源标签')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.resource_spec.spider_slave_ip_list.label_values"
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
  <ResourcePreview
    v-model:is-show="showSlider"
    :params="params" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { DBTypes, TicketTypes } from '@common/const';

  import ResourcePreview from '@views/db-manage/common/toolbox-field/column/available-resource-column/components/ResourcePreview.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderSlaveApply>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY,
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
      labels: data.resource_spec.spider_slave_ip_list.labels.join(','),
      resource_types: [DBTypes.TENDBCLUSTER, 'PUBLIC'],
      spec_id: data.resource_spec.spider_slave_ip_list.spec_id,
    };
  };
</script>
