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
    show-overflow-tooltip>
    <BkTableColumn
      field="bill_id"
      :label="t('关联单据')"
      :min-width="130" />
    <BkTableColumn
      field="src_cluster"
      :label="t('源集群')"
      :min-width="220" />
    <BkTableColumn
      field="src_instances"
      :label="t('源实例')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <span v-if="_.isEqual(['all'], data.src_instances)">{{ t('全部') }}</span>
        <TagBlock
          v-else
          :data="data.src_instances" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="dst_cluster"
      :label="t('目标集群')"
      :min-width="220" />
    <BkTableColumn :label="t('包含 Key')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="generateSplitList(data.key_white_regex)" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('排除 Key')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="generateSplitList(data.key_black_regex)" />
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('执行模式:')">
      {{ executeModesMap[ticketDetails.details.execute_mode] }}
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.execute_mode === 'scheduled_execution'"
      :label="t('指定执行时间')">
      {{ utcDisplayTime(ticketDetails.details.specified_execution_time) }}
    </InfoItem>
    <InfoItem :label="t('指定停止时间')">
      {{ utcDisplayTime(ticketDetails.details.check_stop_time) }}
    </InfoItem>
    <InfoItem :label="t('一直保持校验修复')">
      {{ ticketDetails.details.keep_check_and_repair ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('修复数据')">
      {{ ticketDetails.details.data_repair_enabled ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('修复模式')">
      {{ repairModesMap[ticketDetails.details.repair_mode] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import { utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.DatacopyCheckRepair>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][0];

  defineOptions({
    name: TicketTypes.REDIS_DATACOPY_CHECK_REPAIR,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const executeModesMap: Record<string, string> = {
    auto_execution: t('自动执行'),
    scheduled_execution: t('定时执行'),
  };

  const repairModesMap: Record<string, string> = {
    auto_repair: t('自动修复'),
    manual_confirm: t('人工确认'),
  };

  const generateSplitList = (str: string) => (str ? str.split('\n') : []);
</script>
