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
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('备份位置')">
      <template #default="{ data }: { data: RowData }">
        {{ data.backup_local }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('备份类型:')">
      {{ backupType }}
    </InfoItem>
    <InfoItem :label="t('备份保存时间:')">
      {{ backupTime }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.FullBackup>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_FULL_BACKUP,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  // 备份类型
  const backupType = computed(() => {
    if (props.ticketDetails.details.backup_type === 'physical') {
      return t('物理备份');
    }
    return t('逻辑备份');
  });

  const fileTagMap: Record<string, string> = {
    DBFILE1M: t('1个月'),
    DBFILE6M: t('6个月'),
    DBFILE1Y: t('1年'),
    DBFILE3Y: t('3年'),
  };
  // 备份保存时间
  const backupTime = computed(() => {
    const fileTag = props.ticketDetails.details.file_tag;
    if (!fileTagMap[fileTag]) {
      // 兼容旧单据
      if (fileTag === 'LONGDAY_DBFILE_3Y') {
        return t('3年');
      }
      return t('30天');
    }
    return fileTagMap[fileTag];
  });
</script>
