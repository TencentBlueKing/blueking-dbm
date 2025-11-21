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
    :width="900"
    @close="handleClose">
    <template #header>
      <span>{{ t('最终DB') }}</span>
      <BkTag class="ml-10">{{ t('源集群：') }}{{ rowData.cluster.master_domain }}</BkTag>
    </template>
    <div class="mysql-data-migrate-priview-dbs">
      <EditableTable
        ref="table"
        class="mb-20"
        :model="editTableData">
        <EditableRow
          v-for="(item, index) in editTableData"
          :key="index">
          <DbNameColumn
            v-model="item.clone_db_list"
            check-not-exist
            :cluster-id="item.cluster?.id"
            field="clone_db_list"
            :label="t('克隆DB名')"
            :show-edit-icon="false" />
          <DbNameColumn
            v-model="item.ignore_db_list"
            :cluster-id="item.cluster?.id"
            field="ignore_db_list"
            :label="t('忽略DB名')"
            :required="false"
            :show-edit-icon="false" />
        </EditableRow>
      </EditableTable>
      <BkLoading :loading="loading">
        <BkTable :data="tableData">
          <BkTableColumn
            field="dbname"
            :label="t('最终DB')">
            <template #header>
              <span>{{ t('最终DB') }}（{{ tableData.length }}）</span>
              <DbIcon
                class="copy-btn"
                type="copy"
                @click="handleCopy" />
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

  import DbNameColumn from '@views/db-manage/mysql/common/edit-table-column/DbNameColumn.vue';

  import { execCopy } from '@utils';

  import { showDatabasesWithPatterns } from '@services/source/remoteService';

  interface RowData {
    dbname: string;
  }

  interface Props {
    rowData: {
      clone_db_list: string[];
      cluster: TendbhaModel;
      data_schema_grant: string;
      db_list: string[];
      ignore_db_list: string[];
      target_clusters: TendbhaModel[];
    };
  }

  type Emits = (
    e: 'change',
    data: {
      clone_db_list: string[];
      db_list: string[];
      ignore_db_list: string[];
    },
  ) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  const tableData = shallowRef<RowData[]>([]);
  const editTableData = ref<Props['rowData'][]>([]);

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
      editTableData.value = [
        {
          ...props.rowData,
        },
      ];
    }
  });

  watch(
    editTableData,
    () => {
      if (props.rowData.cluster.id && editTableData.value[0].clone_db_list.length) {
        fetchData({
          infos: [
            {
              cluster_id: props.rowData.cluster.id,
              dbs: editTableData.value[0].clone_db_list,
              ignore_dbs: editTableData.value[0]?.ignore_db_list || [],
            },
          ],
        });
      }
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleCopy = () => {
    const list = tableData.value.map((item) => item.dbname);
    execCopy(list.join('\n'), t('复制成功，共n条', { n: list.length }));
  };

  const handleClose = () => {
    emits('change', {
      clone_db_list: editTableData.value[0].clone_db_list,
      db_list: tableData.value.map((item) => item.dbname),
      ignore_db_list: editTableData.value[0].ignore_db_list,
    });
  };
</script>
<style lang="less" scoped>
  .mysql-data-migrate-priview-dbs {
    margin: 18px 24px;

    .copy-btn {
      padding-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
