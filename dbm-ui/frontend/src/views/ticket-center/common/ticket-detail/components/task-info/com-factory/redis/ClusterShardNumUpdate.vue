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
      :label="t('源集群')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('架构版本')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('当前集群容量/QPS')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{
          `${data.capacity}G_${ticketDetails.details.specs[data.resource_spec.backend_group.spec_id].qps.max}/s(${data.current_shard_num}片)`
        }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="capacity"
      :label="t('当前容量需求')" />
    <BkTableColumn
      field="future_capacity"
      :label="t('未来容量需求')" />
    <BkTableColumn
      :label="t('部署方案')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.specs[data.resource_spec.backend_group.spec_id].name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="db_version"
      :label="t('版本')" />
    <BkTableColumn :label="t('切换模式')">
      <template #default="{ data }: { data: RowData }">
        {{ data.online_switch_type === 'user_confirm' ? t('需人工确认') : t('无需确认') }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('校验与修复类型:')">
      {{ repairAndVerifyTypesMap[ticketDetails.details.data_check_repair_setting.type] }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.data_check_repair_setting.type !== 'no_check_no_repair'"
      :label="t('校验与修复频率设置:')">
      {{ repairAndVerifyFrequencyMap[ticketDetails.details.data_check_repair_setting.execution_frequency] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { repairAndVerifyFrequencyList, repairAndVerifyTypeList } from '@views/db-manage/redis/common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterShardNumUpdate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_SHARD_NUM_UPDATE,
    inheritAttrs: false,
  });

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
