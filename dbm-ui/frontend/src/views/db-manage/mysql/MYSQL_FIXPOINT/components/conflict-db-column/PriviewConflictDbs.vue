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
        theme="warning"
        closable>
        {{ t('当前的备份类型为物理备份，受影响的DB 在执行时将强制清空，请谨慎操作') }}
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
  import { showDatabasesWithPatterns } from '@/services/source/remoteService';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  interface RowData {
    dbname: string;
  }

  interface Props {
    rowData: {
      cluster: TendbhaModel;
      databases: string[];
      tables: string[];
    };
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  const tableData = shallowRef<RowData[]>([]);

  const { loading, run: fetchData } = useRequest(showDatabasesWithPatterns, {
    manual: true,
    onSuccess: (data) => {
      tableData.value = (data?.[0]?.databases || []).map((dbname) => ({
        dbname,
      }));
    },
  });

  watch(isShow, () => {
    if (isShow.value) {
      fetchData({
        infos: [
          {
            cluster_id: props.rowData.cluster.id,
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
