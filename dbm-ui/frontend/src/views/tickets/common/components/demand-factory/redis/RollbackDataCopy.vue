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
  <div class="ticket-details__info">
    <div
      class="ticket-details__item"
      style="align-items: flex-start;">
      <span
        class="ticket-details__item-label">{{ t('需求信息') }}：</span>
      <span class="ticket-details__item-value">
        <BkLoading :loading="loading">
          <DbOriginalTable
            :columns="columns"
            :data="tableData" />
        </BkLoading>
      </span>
    </div>
  </div>
  <BkLoading :loading="loading" />
  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('写入类型') }}：</span>
        <span class="ticket-details__item-value">{{ writeTypesMap[ticketDetails.details.write_mode] }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listClusterList } from '@services/redis/toolbox';
  import type { RedisRollbackDataCopyDetails, TicketDetails } from '@services/types/ticket';

  import { writeTypeList } from '@views/redis/common/const';

  interface Props {
    ticketDetails: TicketDetails<RedisRollbackDataCopyDetails>
  }

  interface RowData {
    entry: string,
    taregtClusterName: string,
    time: string,
    includeKeys: string[],
    excludeKeys: string[],
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);

  const writeTypesMap = writeTypeList.reduce((obj, item) => {
    Object.assign(obj, { [item.value]: item.label });
    return obj;
  }, {} as Record<string, string>);

  const columns = [
    {
      label: t('构造产物访问入口'),
      field: 'entry',
    },
    {
      label: t('目标集群'),
      field: 'taregtClusterName',
    },
    {
      label: t('构造到指定时间'),
      field: 'time',
    },
    {
      label: t('包含 Key'),
      field: 'targetNum',
      render: ({ data }: {data: RowData}) => {
        if (data.includeKeys.length > 0) {
          return data.includeKeys.map((key, index) => <bk-tag key={index} type="stroke">{key}</bk-tag>);
        }
        return <span>--</span>;
      },
    },
    {
      label: t('排除 Key'),
      field: 'time',
      render: ({ data }: {data: RowData}) => {
        if (data.excludeKeys.length > 0) {
          return data.excludeKeys.map((key, index) => <bk-tag key={index} type="stroke">{key}</bk-tag>);
        }
        return <span>--</span>;
      },
    },
  ];

  const { loading } = useRequest(listClusterList, {
    onSuccess: async (r) => {
      if (r.length < 1) {
        return;
      }
      const clusterMap = r.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item.master_domain });
        return obj;
      }, {} as Record<string, string>);

      tableData.value = infos.map(item => ({
        entry: item.src_cluster,
        taregtClusterName: clusterMap[item.dst_cluster],
        time: item.recovery_time_point,
        includeKeys: item.key_white_regex === '' ? [] : item.key_white_regex.split('\n'),
        excludeKeys: item.key_black_regex === '' ? [] : item.key_black_regex.split('\n'),
      }));
    },
  });
</script>

<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
