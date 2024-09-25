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
  <DbOriginalTable
    :columns="columns"
    :data="tableData" />
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('备份类型') }}：</span>
      <span class="ticket-details-item-value">{{
        infos.backup_type === 'physical' ? t('物理备份') : t('逻辑备份')
      }}</span>
    </div>
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('备份保存时间') }}：</span>
      <span class="ticket-details-item-value">
        {{ backupTime }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { SpiderFullBackupDetails } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';
  import { getTendbclusterListByBizId } from '@services/source/tendbcluster';

  interface Props {
    ticketDetails: TicketModel<SpiderFullBackupDetails>;
  }

  interface RowData {
    clusterName: string;
    position: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;

  const fileTagMap: Record<string, string> = {
    DBFILE1M: t('1个月'),
    DBFILE6M: t('6个月'),
    DBFILE1Y: t('1年'),
    DBFILE3Y: t('3年'),
  };

  const columns = [
    {
      label: t('目标集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('备份位置'),
      field: 'position',
      showOverflowTooltip: true,
    },
  ];

  const tableData = ref<RowData[]>([]);

  // 备份保存时间
  const backupTime = computed(() => {
    const fileTag = props.ticketDetails.details.infos.file_tag;
    if (!fileTagMap[fileTag]) {
      // 兼容旧单据
      if (fileTag === 'LONGDAY_DBFILE_3Y') {
        return t('3年');
      }
      return t('30天');
    }
    return fileTagMap[fileTag];
  });

  useRequest(getTendbclusterListByBizId, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        offset: 0,
        limit: -1,
      },
    ],
    onSuccess: (r) => {
      if (r.results.length < 1) {
        return;
      }
      const clusterMap = r.results.reduce<Record<number, string>>((obj, item) => {
        Object.assign(obj, { [item.id]: item.master_domain });
        return obj;
      }, {});
      tableData.value = infos.clusters.reduce<RowData[]>((results, item) => {
        const obj = {
          clusterName: clusterMap[item.cluster_id],
          position: item.backup_local,
        };
        results.push(obj);
        return results;
      }, []);
    },
  });
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
