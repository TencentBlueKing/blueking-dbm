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
        class="ticket-details__item-label">{{ t('复制信息') }}：</span>
      <span class="ticket-details__item-value">
        <BkLoading :loading="loading">
          <DbOriginalTable
            :columns="columns"
            :data="tableData" />
        </BkLoading>
      </span>
    </div>
  </div>

  <div class="ticket-details__info">
    <div class="ticket-details__list">
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('复制类型') }}：</span>
        <span class="ticket-details__item-value">{{ copyTypesMap[ticketDetails.details.dts_copy_type] }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('写入类型') }}：</span>
        <span class="ticket-details__item-value">{{ writeTypesMap[ticketDetails.details.write_mode] }}</span>
      </div>
      <div class="ticket-details__item">
        <span class="ticket-details__item-label">{{ t('断开设置') }}：</span>
        <span class="ticket-details__item-value">
          {{ disconnectTypesMap[ticketDetails.details.sync_disconnect_setting.type] }}
        </span>
      </div>
      <template v-if="ticketDetails.details.sync_disconnect_setting.type !== 'auto_disconnect_after_replication'">
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('提醒频率') }}：</span>
          <span class="ticket-details__item-value">
            {{ remindFrequencyTypesMap[ticketDetails.details.sync_disconnect_setting.reminder_frequency] }}
          </span>
        </div>
        <div class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('校验与修复类型') }}：</span>
          <span class="ticket-details__item-value">
            {{ repairAndVerifyTypesMap[ticketDetails.details.data_check_repair_setting.type] }}
          </span>
        </div>
        <div
          v-if="ticketDetails.details.data_check_repair_setting.type !== 'no_check_no_repair'"
          class="ticket-details__item">
          <span class="ticket-details__item-label">{{ t('校验与修复频率设置') }}：</span>
          <span class="ticket-details__item-value">
            {{ repairAndVerifyFrequencyTypesMap[ticketDetails.details.data_check_repair_setting.execution_frequency] }}
          </span>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRedisListByBizId } from '@services/source/redis';
  import type { RedisDataCopyDetails, TicketDetails } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import {
    copyTypeList,
    disconnectTypeList,
    remindFrequencyTypeList,
    repairAndVerifyFrequencyList,
    repairAndVerifyTypeList,
    writeTypeList,
  } from '@views/redis/common/const';

  interface Props {
    ticketDetails: TicketDetails<RedisDataCopyDetails>
  }

  const props = defineProps<Props>();

  type RawRowData = RedisDataCopyDetails['infos'][0]

  interface RowData {
    srcClusterName: string,
    srcClusterType: string,
    dstClusterName: string,
    dstDiz: string,
    includeKeys: string[],
    excludeKeys: string[],
  }

  // 生成行数据
  function generateTableRowData(copyType: string, clusterMap: Record<string, string>, item: RawRowData) {
    let obj: RowData = {
      srcClusterName: '',
      dstClusterName: '',
      srcClusterType: '',
      dstDiz: '',
      includeKeys: item.key_white_regex === '' ? [] : item.key_white_regex.split('\n'),
      excludeKeys: item.key_black_regex === '' ? [] : item.key_black_regex.split('\n'),
    };
    switch (copyType) {
    case 'diff_app_diff_cluster':
      // 跨业务
      obj = {
        ...obj,
        srcClusterName: clusterMap[item.src_cluster],
        dstClusterName: clusterMap[item.dst_cluster],
        dstDiz: bizsMap[item.dst_bk_biz_id],
      };
      break;
    case 'copy_to_other_system':
      // 至第三方
      obj = {
        ...obj,
        srcClusterName: clusterMap[item.src_cluster],
        dstClusterName: item.dst_cluster,
      };
      break;
    case 'one_app_diff_cluster':
      // 业务内
      obj = {
        ...obj,
        srcClusterName: clusterMap[item.src_cluster],
        dstClusterName: clusterMap[item.dst_cluster],
      };

      break;
    case 'user_built_to_dbm':
      // 自建集群至业务内
      obj = {
        ...obj,
        srcClusterName: item.src_cluster,
        srcClusterType: item.src_cluster_type,
        dstClusterName: clusterMap[item.dst_cluster],
      };
      break;
    default:
      break;
    }
    return obj;
  }

  // 生成映射表
  function generateMap(arr: { label: string, value: string}[]) {
    return arr.reduce((obj, item) => {
      Object.assign(obj, { [item.value]: item.label });
      return obj;
    }, {} as Record<string, string>);
  }

  const { t } = useI18n();
  const { bizs } = useGlobalBizs();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);

  const copyTypesMap = generateMap(copyTypeList);

  const disconnectTypesMap = generateMap(disconnectTypeList);

  const remindFrequencyTypesMap = generateMap(remindFrequencyTypeList);

  const repairAndVerifyFrequencyTypesMap = generateMap(repairAndVerifyFrequencyList);

  const repairAndVerifyTypesMap = generateMap(repairAndVerifyTypeList);

  const writeTypesMap = generateMap(writeTypeList);

  const basicColumns = [
    {
      label: t('源集群'),
      field: 'srcClusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('目标集群'),
      field: 'dstClusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('包含 Key'),
      field: 'targetNum',
      showOverflowTooltip: true,
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
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => {
        if (data.excludeKeys.length > 0) {
          return data.excludeKeys.map((key, index) => <bk-tag key={index} type="stroke">{key}</bk-tag>);
        }
        return <span>--</span>;
      },
    },
  ];

  const bizCloumn = {
    label: t('目标业务'),
    field: 'dstDiz',
    showOverflowTooltip: true,
  };

  const clusterTypeColum = {
    label: t('集群类型'),
    field: 'dstDiz',
    showOverflowTooltip: true,
    render: ({ data }: {data: RowData}) => <span>{data.dstDiz === 'RedisInstance' ? t('主从版') : t('集群版')}</span>,
  };

  const columns = computed(() => {
    switch (props.ticketDetails.details.dts_copy_type) {
    case 'copy_to_other_system':
      return basicColumns;
    case 'diff_app_diff_cluster':
      basicColumns.splice(1, 0, bizCloumn);
      return basicColumns;
    case 'one_app_diff_cluster':
      return basicColumns;
    case 'user_built_to_dbm':
      basicColumns.splice(1, 0, clusterTypeColum);
      return basicColumns;
    default:
      return [];
    }
  });

  const bizsMap = bizs.reduce((obj, item) => {
    Object.assign({ bk_biz_id: item.name }, obj);
    return obj;
  }, {} as Record<string, string>);

  const { loading } = useRequest(getRedisListByBizId, {
    defaultParams: [{
      bk_biz_id: props.ticketDetails.bk_biz_id,
      offset: 0,
      limit: -1,
    }],
    onSuccess: async (result) => {
      if (result.results.length < 1) {
        return;
      }
      const clusterMap = result.results.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item.master_domain });
        return obj;
      }, {} as Record<string, string>);

      tableData.value = infos.reduce((results, item) => {
        const obj = generateTableRowData(props.ticketDetails.details.dts_copy_type, clusterMap, item);
        results.push(obj);
        return results;
      }, [] as RowData[]);
    },
  });

</script>
<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
