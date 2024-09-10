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
  <BkLoading :loading="loading">
    <BkTable :data="tableData">
      <BkTableColumn :label="t('目标集群')">
        <template #default="{ data }: { data: RowData }">
          {{ data.clusterName }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('源DB名')">
        <template #default="{ data }: { data: RowData }">
          {{ data.fromName }}
        </template>
      </BkTableColumn>
      <BkTableColumn :label="t('新DB名')">
        <template #default="{ data }: { data: RowData }">
          {{ data.toName }}
        </template>
      </BkTableColumn>
    </BkTable>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';
  import { getSpiderListByBizId } from '@services/source/spider';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.RenameDataBase>;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_RENAME_DATABASE,
  });

  const { t } = useI18n();

  const { infos } = props.ticketDetails.details;
  interface RowData {
    clusterName: string;
    fromName: string;
    toName: string;
  }

  const tableData = ref<RowData[]>([]);

  const { loading } = useRequest(getSpiderListByBizId, {
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
      const clusterMap = r.results.reduce(
        (obj, item) => {
          Object.assign(obj, { [item.id]: item.master_domain });
          return obj;
        },
        {} as Record<number, string>,
      );

      tableData.value = infos.reduce((results, item) => {
        const obj = {
          clusterName: clusterMap[item.cluster_id],
          fromName: item.from_database,
          toName: item.to_database,
        };
        results.push(obj);
        return results;
      }, [] as RowData[]);
    },
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
