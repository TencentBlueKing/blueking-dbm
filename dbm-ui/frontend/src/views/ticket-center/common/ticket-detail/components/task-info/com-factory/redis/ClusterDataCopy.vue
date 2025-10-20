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
  <PrimaryTable
    :data="ticketDetails.details.infos"
    row-key="dst_bk_biz_id">
    <TableColumn
      col-key="src_cluster"
      :min-width="180"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{
          _.isString(row.src_cluster) ? row.src_cluster : ticketDetails.details.clusters[row.src_cluster].immute_domain
        }}
      </template>
    </TableColumn>
    <TableColumn
      v-if="ticketDetails.details.dts_copy_type === 'user_built_to_dbm'"
      col-key="src_cluster_type"
      :title="t('集群类型')">
      <template #default="{ row }: { row: RowData }">
        {{ row.src_cluster_type === 'RedisInstance' ? t('主从版') : t('集群版') }}
      </template>
    </TableColumn>
    <TableColumn
      v-else
      col-key="src_cluster_type"
      :title="t('架构版本')"
      :width="150">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.src_cluster as number].cluster_type_name }}
      </template>
    </TableColumn>
    <TableColumn
      v-if="ticketDetails.details.dts_copy_type === 'diff_app_diff_cluster'"
      col-key="src_bk_biz_id"
      :title="t('目标业务')">
      <template #default="{ row }: { row: RowData }">
        {{ bizsMap[row.dst_bk_biz_id] }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="dst_cluster"
      :min-width="180"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{
          _.isString(row.dst_cluster) ? row.dst_cluster : ticketDetails.details.clusters[row.dst_cluster].immute_domain
        }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="key_white_regex"
      :min-width="240"
      :title="t('包含 Key')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="generateSplitList(row.key_white_regex)" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="key_black_regex"
      :label="t('排除 Key')"
      :min-width="370">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="generateSplitList(row.key_black_regex)" />
      </template>
    </TableColumn>
  </PrimaryTable>
  <InfoList>
    <InfoItem :label="t('复制类型')">
      {{ copyTypesMap[ticketDetails.details.dts_copy_type] }}
    </InfoItem>
    <InfoItem :label="t('写入类型')">
      {{ writeTypesMap[ticketDetails.details.write_mode] }}
    </InfoItem>
    <InfoItem :label="t('断开设置')">
      {{ disconnectTypesMap[ticketDetails.details.sync_disconnect_setting.type] }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.sync_disconnect_setting.type !== 'auto_disconnect_after_replication'"
      :label="t('提醒频率')">
      {{ remindFrequencyTypesMap[ticketDetails.details.sync_disconnect_setting.reminder_frequency] }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.sync_disconnect_setting.type !== 'auto_disconnect_after_replication'"
      :label="t('校验与修复类型')">
      {{ repairAndVerifyTypesMap[ticketDetails.details.data_check_repair_setting.type] }}
    </InfoItem>
    <InfoItem
      v-if="
        ticketDetails.details.sync_disconnect_setting.type !== 'auto_disconnect_after_replication' &&
        ticketDetails.details.data_check_repair_setting.type !== 'no_check_no_repair'
      "
      :label="t('校验与修复频率设置')">
      {{ repairAndVerifyFrequencyTypesMap[ticketDetails.details.data_check_repair_setting.execution_frequency] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

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

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_DATA_COPY,
    inheritAttrs: false,
  });

  defineProps<Props>();

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
