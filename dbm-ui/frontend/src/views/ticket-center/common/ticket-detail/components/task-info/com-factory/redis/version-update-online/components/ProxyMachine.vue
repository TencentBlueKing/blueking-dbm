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
    :data="dataList"
    row-key="ip">
    <TableColumn
      col-key="ip"
      fixed="left"
      :min-width="250"
      :title="t('目标主机')">
    </TableColumn>
    <TableColumn
      col-key="related_clusters"
      :title="t('所属集群')"
      :width="200">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="item in row.related_clusters"
          :key="item">
          {{ item }}
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="current_versions"
      :min-width="250"
      :title="t('当前版本')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="item in row.current_versions"
          :key="item">
          {{ item }}
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="target_version"
      :min-width="250"
      :title="t('目标版本')">
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  type RowData = {
    current_versions: string[];
    ip: string;
    related_clusters: string[];
    target_version: string;
  };

  interface Props {
    ticketDetails: TicketModel<Redis.VersionUpdateOnline>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // 集群维度转换成IP维度
  const { infos } = props.ticketDetails.details;
  const dataList: RowData[] = infos.flatMap((infoItem) =>
    infoItem.target_versions.map((versionItem) => ({
      current_versions: infoItem.current_versions,
      ip: versionItem.ip,
      related_clusters: versionItem.related_clusters,
      target_version: versionItem.version,
    })),
  );
</script>
