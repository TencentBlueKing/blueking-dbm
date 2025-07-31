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
  <BkFormItem :label="t('查询结果')">
    <div class="query-access-source-result-item">
      <div class="results-info-main">
        <div class="counts-display">
          <span>{{ t('查询结果') }}</span>
          <span class="ml-4 mr-4">:</span>
          <I18nT
            keypath="共m条"
            tag="span">
            <span style="font-weight: 700; color: #63656e">{{ tableData.length }}</span>
          </I18nT>
          <span class="ml-4 mr-4">,</span>
          <I18nT
            keypath="耗时：m 秒"
            tag="span">
            <span>{{ querySeconds }}</span>
          </I18nT>
          <span class="ml-4 mr-4">,</span>
          <I18nT
            keypath="全部成功n个集群"
            tag="span">
            <span style="font-weight: 700; color: #2caf5e">{{ successCount }}</span>
          </I18nT>
          <span class="ml-4 mr-4">,</span>
          <I18nT
            keypath="部分失败n个集群"
            tag="span">
            <span style="font-weight: 700; color: #f59500">{{ partialFailedCount }}</span>
          </I18nT>
          <span class="ml-4 mr-4">,</span>
          <I18nT
            keypath="全部失败n个集群"
            tag="span">
            <span style="font-weight: 700; color: #ea3636">{{ failedCount }}</span>
          </I18nT>
        </div>
        <BkButton
          text
          theme="primary"
          @click="handleExport">
          {{ t('导出结果') }}
        </BkButton>
      </div>
      <BkLoading :loading="isTableLoading">
        <BkTable
          border="inner"
          class="query-result-table"
          :data="tableData"
          :merge-cells="mergeCells"
          :remote-pagination="false"
          :row-config="{
            isHover: false,
            height: 28,
          }"
          stripe>
          <BkTableColumn
            field="cluster_domain"
            :label="t('集群')"
            :min-width="200" />
          <BkTableColumn
            field="status"
            :label="t('统计的集群主机')"
            :min-width="200">
            <template #default="{ data }: { data: RowData }">
              <StatusContent
                :error-list="data.error_list"
                :success-list="data.success_list" />
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="remote_ip"
            :label="t('来源 IP')"
            :min-width="200">
            <template #default="{ data }: { data: RowData }">
              {{ data.remote_ip || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="establish"
            :label="t('连接数（ESTAB）')">
            <template #default="{ data }: { data: RowData }">
              {{ data.remote_ip ? data.establish : data.success_list.length ? 0 : '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="all_connections"
            :label="t('连接数（ALL）')">
            <template #default="{ data }: { data: RowData }">
              {{ data.remote_ip ? data.all_connections : data.success_list.length ? 0 : '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="topo"
            :label="t('业务模块')"
            :min-width="200">
            <template #default="{ data }: { data: RowData }">
              {{ data.topo && data.topo.length ? data.topo[0] : '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="operator"
            :label="t('主要负责人')">
            <template #default="{ data }: { data: RowData }">
              {{ data.operator || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bak_operator"
            :label="t('备份负责人')">
            <template #default="{ data }: { data: RowData }">
              {{ data.bak_operator || '--' }}
            </template>
          </BkTableColumn>
        </BkTable>
      </BkLoading>
    </div>
  </BkFormItem>
</template>
<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    executeClusterTcpCmd as mongodbExecuteClusterTcpCmd,
    getClusterNetTcpResult as mongodbGetClusterNetTcpResult,
  } from '@services/source/mongodbToolbox';
  import {
    executeClusterTcpCmd as redisExecuteClusterTcpCmd,
    getClusterNetTcpResult as redisGetClusterNetTcpResult,
  } from '@services/source/redisToolbox';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import { exportExcelFile } from '@utils';

  import { useTimeoutPoll } from '@vueuse/core';

  import StatusContent from './components/StatusContent.vue';

  interface Props {
    clusters?: {
      domain: string;
      id: number;
    }[];
    dbType: DBTypes.REDIS | DBTypes.MONGODB;
  }

  type Emits = (event: 'finish') => void;

  interface Exposes {
    reset(): void;
  }

  type RowData = {
    error_list: string[];
    success_list: string[];
  } & ServiceReturnType<typeof redisGetClusterNetTcpResult>['data'][number]['report'][number];

  const props = withDefaults(defineProps<Props>(), {
    clusters: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const querySeconds = ref(0);
  const isTableLoading = ref(false);
  const successCount = ref(0);
  const failedCount = ref(0);
  const partialFailedCount = ref(0);
  const tableData = ref<RowData[]>([]);
  const mergeCells = ref<
    {
      col: number;
      colspan: number;
      row: number;
      rowspan: number;
    }[]
  >([]);

  let queryStartTime = 0;
  let queryEndTime = 0;

  const initLocalState = () => {
    tableData.value = [];
    mergeCells.value = [];
    querySeconds.value = 0;
    queryStartTime = Date.now();
    successCount.value = 0;
    failedCount.value = 0;
    partialFailedCount.value = 0;
  };

  const apiMap = {
    [DBTypes.MONGODB]: {
      executeClusterTcpCmd: mongodbExecuteClusterTcpCmd,
      getClusterNetTcpResult: mongodbGetClusterNetTcpResult,
    },
    [DBTypes.REDIS]: {
      executeClusterTcpCmd: redisExecuteClusterTcpCmd,
      getClusterNetTcpResult: redisGetClusterNetTcpResult,
    },
  };

  const { data: clusterTcpCmdData, run: handleExecuteClusterTcpCmd } = useRequest(
    apiMap[props.dbType].executeClusterTcpCmd,
    {
      manual: true,
      onSuccess() {
        resumeQueryTableData();
      },
    },
  );

  watch(
    () => props.clusters,
    () => {
      if (props.clusters.length) {
        initLocalState();
        isTableLoading.value = true;
        handleExecuteClusterTcpCmd({ cluster_ids: props.clusters.map((item) => item.id) });
      }
    },
    {
      immediate: true,
    },
  );

  const generateEmptyRow = () => {
    return {
      all_connections: 0,
      bak_operator: '',
      cluster_domain: '',
      error_list: [] as string[],
      establish: 0,
      operator: '',
      remote_ip: '',
      success_list: [] as string[],
      topo: [],
    };
  };

  const queryTableData = async () => {
    try {
      const tcpResult = await apiMap[props.dbType].getClusterNetTcpResult({
        job_instance_id: clusterTcpCmdData.value!.job_instance_id,
      });
      if (tcpResult.finished) {
        emits('finish');
        pauseQueryTableData();
        isTableLoading.value = false;
        queryEndTime = Date.now();
        querySeconds.value = (queryEndTime - queryStartTime) / 1000;
        tcpResult.data.forEach((clusterItem) => {
          if (!clusterItem.error.length) {
            successCount.value += 1;
          }
          if (!clusterItem.success.length) {
            failedCount.value += 1;
          }
          if (clusterItem.error.length && clusterItem.success.length) {
            partialFailedCount.value += 1;
          }
          if (!clusterItem.report.length) {
            // 插入占位行
            const emptyRow = generateEmptyRow();
            emptyRow.error_list = clusterItem.error;
            emptyRow.cluster_domain = clusterItem.cluster_domain;
            emptyRow.success_list = clusterItem.success;
            tableData.value.push(emptyRow);
          } else {
            const newRows = clusterItem.report.map((item) =>
              Object.assign(item, {
                error_list: clusterItem.error,
                success_list: clusterItem.success,
              }),
            );
            mergeCells.value.push(
              {
                col: 0,
                colspan: 1,
                row: tableData.value.length,
                rowspan: newRows.length,
              },
              {
                col: 1,
                colspan: 1,
                row: tableData.value.length,
                rowspan: newRows.length,
              },
            );
            tableData.value.push(...newRows);
          }
        });
      } else {
        resumeQueryTableData();
      }
    } catch (error) {
      isTableLoading.value = false;
      pauseQueryTableData();
      emits('finish');
      throw error;
    }
  };

  const { pause: pauseQueryTableData, resume: resumeQueryTableData } = useTimeoutPoll(queryTableData, 3000);

  const handleExport = () => {
    /* eslint-disable perfectionist/sort-objects */
    const formatData = tableData.value.map((item) => ({
      [t('集群')]: item.cluster_domain,
      [t('统计的集群主机')]: !item.error_list.length
        ? t('全部成功')
        : !item.success_list.length
          ? t('全部失败')
          : t('部分失败'),
      [t('来源 IP')]: item.remote_ip,
      [t('连接数（ESTAB）')]: item.establish,
      [t('连接数（ALL）')]: item.all_connections,
      [t('业务模块')]: item.topo && item.topo.length ? item.topo[0] : '',
      [t('主要负责人')]: item.operator,
      [t('备份负责人')]: item.bak_operator,
    }));
    const colsWidths = Array(8)
      .fill('')
      .map(() => ({ width: 40 }));
    const fileName = `${DBTypeInfos[props.dbType].name}${t('查询访问来源')}${dayjs().format('YYYYMMDDHHmm')}.xlsx`;
    exportExcelFile(formatData, colsWidths, 'Sheet1', fileName);
  };

  onMounted(() => {
    pauseQueryTableData();
  });

  defineExpose<Exposes>({
    reset() {
      initLocalState();
    },
  });
</script>

<style lang="less">
  .query-access-source-result-item {
    display: flex;
    flex-direction: column;
    border: 1px solid #dcdee5;

    .results-info-main {
      display: flex;
      height: 48px;
      padding: 0 16px;
      font-size: 12px;
      background: #fff;
      border-bottom: 1px solid #dcdee5;
      justify-content: space-between;
      align-items: center;

      .counts-display {
        flex: 1;
        display: flex;
        overflow: hidden;

        .fail-list-main {
          margin-right: 20px;
          overflow: hidden;
          flex: 1;

          .copy-icon {
            margin-left: 6px;
            font-size: 14px;
            color: #3a84ff;
            cursor: pointer;
          }
        }
      }
    }

    .query-result-table {
      .vxe-table--header-inner-wrapper {
        height: 28px !important;
      }

      .vxe-header--column {
        padding: 3px 0 !important;
      }

      .vxe-table--append-wrapper {
        border-bottom: none;
      }

      .cluster-host-status {
        display: flex;
        align-items: center;

        .error-count {
          margin-left: 5px;
          color: #ea3636;
        }
      }

      .vxe-table--filter-body {
        max-height: 120px !important;
      }

      .vxe-table--filter-option {
        padding: 0 0 0 8px !important;
        margin: 0;
      }
    }
  }
</style>
