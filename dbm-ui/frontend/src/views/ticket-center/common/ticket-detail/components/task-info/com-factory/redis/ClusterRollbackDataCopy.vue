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
    row-key="src_cluster">
    <TableColumn
      col-key="src_cluster"
      fixed="left"
      :min-width="220"
      :title="t('构造产物访问入口')">
    </TableColumn>
    <TableColumn
      col-key="dst_cluster"
      :title="t('目标集群')"
      :width="150">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.dst_cluster].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="cluster_type_name"
      :title="t('架构版本')"
      :width="150">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.dst_cluster].cluster_type_name }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="recovery_time_point"
      :title="t('构造到指定时间')" />
    <TableColumn
      col-key="key_white_regex"
      :title="t('包含 Key')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="generateSplitList(row.key_white_regex)" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="key_black_regex"
      :title="t('排除 Key')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="generateSplitList(row.key_black_regex)" />
      </template>
    </TableColumn>
  </PrimaryTable>
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
