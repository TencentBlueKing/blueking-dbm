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
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="src_cluster">
    <TicketInfoTableColumn
      col-key="immute_domain"
      fixed="left"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.src_cluster].immute_domain"
      :min-width="180"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.src_cluster].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type_name"
      :min-width="130"
      :title="t('源集群类型')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.src_cluster].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="capacity"
      :min-width="150"
      :title="t('源集群容量')">
      <template #default="{ row }: { row: RowData }">
        {{
          `${row.capacity}G_${ticketDetails.details.specs[row.resource_spec.backend_group.spec_id].qps.max || 0}/s(${row.current_shard_num}分片)`
        }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_cluster_type"
      :min-width="130"
      :title="t('新集群类型')" />
    <!-- <TicketInfoTableColumn
      col-key="capacity"
      :title="t('当前容量需求')" />
    <TicketInfoTableColumn
      col-key="future_capacity"
      :title="t('未来容量需求')" /> -->
    <TicketInfoTableColumn
      col-key="db_version"
      :title="t('新集群版本')" />
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="150"
      :title="t('新集群部署方案')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.specs[row.resource_spec.backend_group.spec_id].name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.resource_spec.backend_group?.label_names?.length">
          <DbTag
            v-for="item in row.resource_spec.backend_group.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="online_switch_type"
      :title="t('切换模式')"
      :width="100">
      <template #default="{ row }: { row: RowData }">
        {{ row.online_switch_type === 'user_confirm' ? t('需人工确认') : t('无需确认') }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
  <InfoList>
    <InfoItem :label="t('校验与修复类型')">
      {{ repairAndVerifyTypesMap[ticketDetails.details.data_check_repair_setting.type] }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.data_check_repair_setting.type !== 'no_check_no_repair'"
      :label="t('校验与修复频率设置')">
      {{ repairAndVerifyFrequencyMap[ticketDetails.details.data_check_repair_setting.execution_frequency] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { repairAndVerifyFrequencyList, repairAndVerifyTypeList } from '@views/db-manage/redis/common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ResourcePool.ClusterTypeUpdate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_TYPE_UPDATE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const repairAndVerifyTypesMap = generateMap(repairAndVerifyTypeList);

  const repairAndVerifyFrequencyMap = generateMap(repairAndVerifyFrequencyList);

  // 生成映射表
  function generateMap(arr: { label: string; value: string }[]) {
    return arr.reduce<Record<string, string>>((obj, item) => {
      Object.assign(obj, { [item.value]: item.label });
      return obj;
    }, {});
  }
</script>
