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
  <BkSideslider
    v-model:is-show="isShow"
    :width="900">
    <template #header>
      <span>{{ t('受影响的 DB') }}</span>
      <BkTag class="ml-10">{{ t('源集群：') }}{{ rowData.cluster.master_domain }}</BkTag>
      <BkTag
        v-for="item in rowData.databases"
        :key="item"
        class="ml-4">
        {{ t('源 DB：') }}{{ item }}
      </BkTag>
      <BkTag
        v-for="item in rowData.databases"
        :key="item"
        class="ml-4">
        {{ t('源表：') }}{{ item }}
      </BkTag>
    </template>
    <div class="priview-conflict-dbs">
      <BkAlert
        class="mb-16"
        closable
        theme="warning">
        {{
          t('当前备份记录为backup_method、backup_type。注意：tip', {
            backup_method: backupMethodMap[rowData.backupRecord?.backup_method],
            backup_type: rowData.backupRecord?.backup_type === 'logical' ? t('逻辑备份') : t('物理备份'),
            tip: props.disabled ? t('受影响的DB在执行时将被强制清空，请谨慎操作！') : t('受影响的DB需在执行前手动清档'),
          })
        }}
      </BkAlert>
      <BkLoading :loading="loading">
        <BkTable :data="tableData">
          <BkTableColumn
            field="dbname"
            :label="t('受影响的 DB')">
            <template #header>
              <span>{{ t('受影响的 DB') }}（{{ tableData.length }}）</span>
            </template>
            <template #default="{ row }">
              <span>{{ row.dbname }}</span>
            </template>
          </BkTableColumn>
        </BkTable>
      </BkLoading>
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { type BackupLogRecord } from '@services/source/fixpointRollback';
  import { showDatabasesWithPatterns } from '@services/source/remoteService';

  interface RowData {
    dbname: string;
  }

  interface Props {
    /**
     * 指源库表是否可编辑
     * true：默认*，不可编辑
     * false: 可填
     */
    disabled: boolean;
    rowData: {
      backupRecord: BackupLogRecord;
      cluster: TendbhaModel;
      databases: string[];
      tables: string[];
      targetCluster?: TendbhaModel;
    };
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  const tableData = shallowRef<RowData[]>([]);

  const backupMethodMap = {
    full_by_regular: t('全库备份（例行）'),
    full_by_ticket: t('全库备份（单据）'),
    non_full_by_regular: t('非全库备份（例行）'), // 过滤掉，不展示
    partial_by_ticket: t('库表备份（单据）'),
  } as Record<string, string>;

  const { loading, run: fetchData } = useRequest(showDatabasesWithPatterns, {
    manual: true,
    onSuccess: (data) => {
      let dataList = data?.[0]?.databases || [];
      if (!props.disabled) {
        // 可填时需根据备份记录的 database_list 与目标集群的 db 列表取交集
        dataList = dataList.filter((item) => props.rowData.backupRecord?.database_list.includes(item));
      }
      tableData.value = dataList.map((item) => ({
        dbname: item,
      }));
    },
  });

  watch(isShow, () => {
    if (isShow.value) {
      const clusterId = props.rowData.targetCluster?.id || props.rowData.cluster.id;
      fetchData({
        infos: [
          {
            cluster_id: clusterId,
            dbs: props.rowData.databases,
            ignore_dbs: [],
          },
        ],
      });
    }
  });
</script>
<style lang="less">
  .priview-conflict-dbs {
    margin: 18px 24px;
  }
</style>
