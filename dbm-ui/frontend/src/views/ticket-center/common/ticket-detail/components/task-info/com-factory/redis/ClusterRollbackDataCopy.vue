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
      field="src_cluster"
      fixed="left"
      :label="t('构造产物访问入口')"
      :min-width="220">
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标集群')"
      :width="150">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.dst_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('架构版本')"
      :width="150">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.dst_cluster].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="recovery_time_point"
      :label="t('构造到指定时间')" />
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
    <InfoItem :label="t('写入类型')">
      {{ writeTypesMap[ticketDetails.details.write_mode] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import { writeTypeList } from '@views/db-manage/redis/common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type RowData = TicketModel<Redis.ClusterRollbackDataCopy>['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterRollbackDataCopy>;
  }

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const writeTypesMap = writeTypeList.reduce(
    (obj, item) => {
      Object.assign(obj, { [item.value]: item.label });
      return obj;
    },
    {} as Record<string, string>,
  );

  const generateSplitList = (str: string) => (str ? str.split('\n') : []);
</script>
