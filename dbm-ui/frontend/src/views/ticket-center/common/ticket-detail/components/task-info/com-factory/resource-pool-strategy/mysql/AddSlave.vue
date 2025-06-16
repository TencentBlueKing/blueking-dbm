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
  <InfoList>
    <InfoItem :label="t('主机选择方式')">
      {{ ticketDetails.details.source_type === SourceType.RESOURCE_AUTO ? t('资源池自动匹配') : t('资源池手动选择') }}
    </InfoItem>
  </InfoList>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      fixed="left"
      :label="t('目标集群')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('机器规格')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.specs?.[data.resource_spec.new_slave.spec_id]?.name || '--' }}
      </template>
    </BkTableColumn>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_AUTO">
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
    </template>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_MANUAL">
      <BkTableColumn
        :label="t('新从库主机')"
        :min-width="120">
        <template #default="{ data }: { data: RowData }">
          {{ data.resource_spec.new_slave.hosts?.[0]?.ip || '--' }}
        </template>
      </BkTableColumn>
    </template>
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
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  import { DBTypes, TicketTypes } from '@common/const';

  import ResourcePreview from '@views/db-manage/common/toolbox-field/column/available-resource-column/components/ResourcePreview.vue';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.AddSlave>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_ADD_SLAVE,
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
      resource_types: [DBTypes.MYSQL, 'PUBLIC'],
      spec_id: data.resource_spec.new_slave.spec_id,
    };
  };
</script>
