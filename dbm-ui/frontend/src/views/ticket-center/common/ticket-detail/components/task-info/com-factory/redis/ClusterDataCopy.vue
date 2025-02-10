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
    <BkTableColumn
      v-if="ticketDetails.details.dts_copy_type === 'user_built_to_dbm'"
      :label="t('集群类型')">
      <template #default="{ data }: { data: RowData }">
        {{ data.src_cluster_type === 'RedisInstance' ? t('主从版') : t('集群版') }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-else
      :label="t('架构版本')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="ticketDetails.details.dts_copy_type === 'diff_app_diff_cluster'"
      :label="t('目标业务')">
      <template #default="{ data }: { data: RowData }">
        {{ bizsMap[data.dst_bk_biz_id] }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.dst_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('包含 Key')"
      :min-width="240">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in generateSplitList(data.key_white_regex)"
          :key="item">
          {{ item }}
        </BkTag>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('排除 Key')"
      :min-width="370">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in generateSplitList(data.key_black_regex)"
          :key="item">
          {{ item }}
        </BkTag>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('复制类型：')">
      {{ copyTypesMap[ticketDetails.details.dts_copy_type] }}
    </InfoItem>
    <InfoItem :label="t('写入类型：')">
      {{ writeTypesMap[ticketDetails.details.write_mode] }}
    </InfoItem>
    <InfoItem :label="t('断开设置：')">
      {{ disconnectTypesMap[ticketDetails.details.sync_disconnect_setting.type] }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.sync_disconnect_setting.type !== 'auto_disconnect_after_replication'"
      :label="t('提醒频率：')">
      {{ remindFrequencyTypesMap[ticketDetails.details.sync_disconnect_setting.reminder_frequency] }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.sync_disconnect_setting.type !== 'auto_disconnect_after_replication'"
      :label="t('校验与修复类型：')">
      {{ repairAndVerifyTypesMap[ticketDetails.details.data_check_repair_setting.type] }}
    </InfoItem>
    <InfoItem
      v-if="
        ticketDetails.details.sync_disconnect_setting.type !== 'auto_disconnect_after_replication' &&
        ticketDetails.details.data_check_repair_setting.type !== 'no_check_no_repair'
      "
      :label="t('校验与修复频率设置：')">
      {{ repairAndVerifyFrequencyTypesMap[ticketDetails.details.data_check_repair_setting.execution_frequency] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import {
    copyTypeList,
    disconnectTypeList,
    remindFrequencyTypeList,
    repairAndVerifyFrequencyList,
    repairAndVerifyTypeList,
    writeTypeList,
  } from '@views/db-manage/redis/common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterDataCopy>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_DATA_COPY,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const { bizs } = useGlobalBizs();

  // 生成映射表
  function generateMap(arr: { label: string; value: string }[]) {
    return arr.reduce(
      (obj, item) => {
        Object.assign(obj, { [item.value]: item.label });
        return obj;
      },
      {} as Record<string, string>,
    );
  }

  const copyTypesMap = generateMap(copyTypeList);

  const disconnectTypesMap = generateMap(disconnectTypeList);

  const remindFrequencyTypesMap = generateMap(remindFrequencyTypeList);

  const repairAndVerifyFrequencyTypesMap = generateMap(repairAndVerifyFrequencyList);

  const repairAndVerifyTypesMap = generateMap(repairAndVerifyTypeList);

  const writeTypesMap = generateMap(writeTypeList);

  const bizsMap = generateMap(bizs.map((item) => ({ label: item.name, value: item.bk_biz_id.toString() })));

  const generateSplitList = (str: string) => (str ? str.split('\n') : []);
</script>
