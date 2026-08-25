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
  <div
    v-if="isShowResults"
    class="assessment-result">
    <div class="mt-24 mb-12 assessment-result-title">
      {{ t('评估结果') }}
    </div>
    <BkLoading
      v-if="isLoading"
      class="assessment-loading-wrapper"
      loading
      mode="spin"
      :opacity="1"
      theme="primary"
      :title="t('正在评估中，请稍等…')" />
    <div v-else>
      <BkAlert
        v-if="seriousRiskClusters.length"
        class="mb-12"
        closable
        theme="danger">
        <template #title>
          <I18nT keypath="磁盘评估未通过，存在n个严重风险的集群">
            <span class="danger-count">{{ seriousRiskClusters.length }}</span>
          </I18nT>
        </template>
      </BkAlert>
      <BkAlert
        v-else
        class="mb-12"
        closable
        theme="success"
        :title="t('磁盘评估通过。')" />
      <PrimaryTable
        bordered
        :data="results"
        :max-height="400"
        row-key="row_key">
        <TableColumn
          col-key="source"
          :min-width="180"
          :title="t('源集群')" />
        <TableColumn
          col-key="db_list"
          :title="t('最终 DB')"
          :width="100">
          <template #default="{ row }: { row: MysqlMergeDiskSpaceModel }">
            <BkButton
              text
              theme="primary"
              @click="handleViewDetail(row)">
              {{ row.db_list.length }}
            </BkButton>
          </template>
        </TableColumn>
        <TableColumn
          col-key="target"
          :min-width="180"
          :title="t('目标集群')" />
        <TableColumn
          col-key="disk_size.used_percent"
          :min-width="180"
          :title="t('当前磁盘使用率')">
          <template #default="{ row }">
            <div class="usage-assessment">
              <BkProgress
                v-if="row.disk_size?.used_percent"
                bg-color="#EAEBF0"
                class="mr-8"
                :color="suggestionColorMap[row.suggestion]"
                :percent="calcDiskUsage(row.disk_size.used_percent)"
                :show-text="false"
                stroke-linecap="square"
                :stroke-width="14"
                type="circle"
                :width="20" />
              {{
                row.disk_size?.used_percent
                  ? `${row.disk_size.used_percent}(${bytePretty(row.disk_size?.used)}/${bytePretty(row.disk_size?.total)})`
                  : '--'
              }}
            </div>
          </template>
        </TableColumn>
        <TableColumn
          col-key="disk_size.used_percent_future"
          :min-width="180"
          :title="t('合并后磁盘预估使用率')">
          <template #title>
            <div style="display: none">
              <div
                ref="popRef"
                class="used-percent-future-pop-wrapper">
                <div class="used-percent-future-title">
                  {{ t('合并后磁盘预估使用率') }}
                </div>
                <p>{{ t('1. 计算基准：磁盘容量、DB 大小取最近上报数据作为统计依据，非实时统计；') }}</p>
                <p>{{ t('2. 使用率范围：') }}</p>
                <ul>
                  <li>{{ t('最小预估：按源 DB 实际大小计算未来磁盘使用率；') }}</li>
                  <li>{{ t('最大预估：按源 DB 容量的 2 倍计算未来磁盘使用率') }}</li>
                </ul>
              </div>
            </div>
            <div
              ref="rootRef"
              class="used-percent-future">
              {{ t('合并后磁盘预估使用率') }}
            </div>
          </template>
          <template #default="{ row }: { row: MysqlMergeDiskSpaceModel }">
            <span :class="`${suggestionMap[row.suggestion]}-color`">
              {{ row.disk_size?.used_percent_future || '--' }}
            </span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="suggestion"
          :min-width="150"
          :title="t('评估结果')">
          <template #default="{ row }">
            <BkTag :theme="suggestionMap[row.suggestion]">
              {{ row.suggestion }}
            </BkTag>
          </template>
        </TableColumn>
      </PrimaryTable>
    </div>

    <PriviewDbs
      v-if="selectedRow"
      v-model:is-show="isShowSlider"
      :data="selectedRow" />
  </div>
</template>

<script lang="ts" setup>
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type MysqlMergeDiskSpaceModel from '@services/model/mysql/mysql-merge-disk-space';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import { mergeDiskSpace } from '@services/source/mysqlToolbox';
  import { showDatabasesWithPatterns } from '@services/source/remoteService';

  import { bytePretty, random } from '@utils';

  import PriviewDbs from './components/PriviewDbs.vue';

  interface RowData {
    clone_db_list: string[];
    data_schema_grant?: string;
    db_list?: string[];
    ignore_db_list: string[];
    source_cluster: TendbhaModel;
    target_clusters: TendbhaModel[];
  }

  const tableData = defineModel<RowData[]>('tableData', {
    required: true,
  });

  const { t } = useI18n();

  const isShowResults = ref(false);
  const results = ref<MysqlMergeDiskSpaceModel[]>([]);
  const seriousRiskClusters = ref<MysqlMergeDiskSpaceModel[]>([]);
  const isShowSlider = ref(false);
  const selectedRow = ref<MysqlMergeDiskSpaceModel>();
  const isLoading = ref(false);
  const rootRef = ref();
  const popRef = ref();
  let tippyIns: Instance | undefined;

  const suggestionMap = {
    严重风险: 'danger',
    安全: 'success',
    轻度风险: 'warning',
  } as Record<string, 'danger' | 'success' | 'warning' | 'info' | undefined>;

  const suggestionColorMap = {
    严重风险: '#ea3636',
    安全: '#2dcb56',
    无源集群db大小上报数据: '',
    无目标集群磁盘上报数据: '',
    轻度风险: '#ff9c01',
  } as Record<string, string>;

  const { run: runAssessment } = useRequest(mergeDiskSpace, {
    manual: true,
    onSuccess(data: MysqlMergeDiskSpaceModel[]) {
      results.value = data.map((item) =>
        Object.assign(item, {
          row_key: random(),
        }),
      );
      seriousRiskClusters.value = data.filter((item) => item.suggestion === '严重风险');
      isLoading.value = false;
      setTimeout(() => {
        if (rootRef.value && popRef.value) {
          tippyIns = tippy(rootRef.value as SingleTarget, {
            allowHTML: true,
            appendTo: () => document.body,
            arrow: true,
            content: popRef.value,
            hideOnClick: true,
            interactive: true,
            maxWidth: 'none',
            offset: [0, 8],
            placement: 'top',
            theme: 'light',
            trigger: 'mouseenter click',
            zIndex: 999999,
          });
        }
      }, 60);
    },
  });

  const { run: fetchDataList } = useRequest(showDatabasesWithPatterns, {
    manual: true,
    onSuccess(dataList) {
      let rowIndex = 0;
      // 源集群 目标集群一对一
      // 响应数据每两行对应表格一行
      const clusterDbsMap: Record<string, string[]> = {};

      // 按两两分组处理 dataList
      for (let i = 0; i < dataList.length; i += 2) {
        const sourceCluster = dataList[i];
        const targetCluster = dataList[i + 1];

        let mergedDatabases: string[] = [];

        // 合并源集群的数据库列表
        if (sourceCluster) {
          mergedDatabases = mergedDatabases.concat(sourceCluster.databases);
        }

        // 合并目标集群的数据库列表
        if (targetCluster) {
          mergedDatabases = mergedDatabases.concat(targetCluster.databases);
        }

        // 将合并后的数据库列表分配给当前行（去重处理）
        clusterDbsMap[rowIndex] = [...new Set(mergedDatabases)];
        rowIndex += 1;
      }

      runAssessment({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        factor: 2, // db合并传2
        migrations: tableData.value.map((item, rowIndex) => ({
          clone_db_list: item.clone_db_list,
          db_list: clusterDbsMap[rowIndex],
          ignore_db_list: item.ignore_db_list,
          source_cluster: item.source_cluster.id,
          target_clusters: item.target_clusters.map((cluster) => cluster.id),
        })),
      });
    },
  });

  const calcDiskUsage = (value: string) => {
    const match = value.match(/(\d+(?:\.\d+)?)/);
    if (match) {
      return parseFloat(match[1]);
    }
    return 0;
  };

  const handleViewDetail = (data: MysqlMergeDiskSpaceModel) => {
    isShowSlider.value = true;
    selectedRow.value = data;
  };

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });

  defineExpose({
    reset() {
      isShowResults.value = false;
      results.value = [];
      seriousRiskClusters.value = [];
      isShowSlider.value = false;
      selectedRow.value = undefined;
    },
    run() {
      if (tableData.value.length) {
        // 渲染结果页
        isShowResults.value = true;

        const infos = tableData.value.reduce<ServiceParameters<typeof showDatabasesWithPatterns>['infos']>(
          (acc, item) => {
            acc.push({
              cluster_id: item.source_cluster.id,
              dbs: item.clone_db_list,
              ignore_dbs: item.ignore_db_list,
            });
            item.target_clusters.forEach((cluster) => {
              acc.push({
                cluster_id: cluster.id,
                dbs: item.clone_db_list,
                ignore_dbs: item.ignore_db_list,
              });
            });
            return acc;
          },
          [],
        );

        isLoading.value = true;
        fetchDataList({ infos });
      }
    },
  });
</script>

<style lang="less">
  .assessment-result {
    .assessment-result-title {
      font-family: MicrosoftYaHei-Bold;
      font-weight: 700;
      font-size: 14px;
      color: #313238;
      letter-spacing: 0;
      line-height: 22px;
    }

    .assessment-loading-wrapper {
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 400px;
      width: 100%;

      .bk-loading-indicator {
        align-items: center;
      }
    }

    .used-percent-future {
      width: fit-content;
      border-bottom: 1px dashed #979ba5;
    }

    .usage-assessment {
      display: flex;
      align-items: center;
    }

    .danger-count {
      font-weight: bolder;
      color: @danger-color;
    }

    .success-color {
      color: @success-color;
    }

    .warning-color {
      color: @warning-color;
    }

    .danger-color {
      color: @danger-color;
    }
  }

  .used-percent-future-pop-wrapper {
    padding: 10px;
    font-family: MicrosoftYaHei;
    font-size: 12px;
    color: #4d4f56;
    letter-spacing: 0;
    line-height: 24px;

    .used-percent-future-title {
      font-weight: 700;
      color: #313238;
      line-height: 20px;
      margin-bottom: 8px;
    }

    ul {
      margin-left: 12px;
    }

    li {
      // 移除默认的列表样式
      list-style: none;
      position: relative;
      padding-left: 12px; // 为小点留出空间

      // 使用伪元素创建小尺寸的点
      &::before {
        content: '';
        position: absolute;
        left: 0;
        top: 50%;
        transform: translateY(-50%);
        width: 4px; // 点的宽度
        height: 4px; // 点的高度
        background: #63656e; // 点的颜色
        border-radius: 50%; // 圆形
      }
    }
  }
</style>
