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
  <EditableTable
    ref="editableTable"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <ClusterInputColumn
        v-model="item.src_cluster"
        field="src_cluster"
        :label="t('源集群')">
      </ClusterInputColumn>
      <ClusterTypeColumn v-model="item.src_cluster_type" />
      <AccessCodeColumn
        v-model="item.src_cluster_password"
        data-copy-type="copy_to_other_system"
        field="src_cluster_password"
        :label="t('访问密码')"
        :params="{
          dstCluster: String(item.dst_cluster.id),
          srcCluster: item.src_cluster,
        }">
      </AccessCodeColumn>
      <RenderTargetCluster
        v-model="item.dst_cluster.id"
        v-model:cluster-name="item.dst_cluster.domain" />
      <RegexKeysColumn
        v-model="item.key_white_regex"
        field="key_white_regex"
        :label="t('包含 Key')"
        required
        @batch-edit="handleColumnBatchEdit">
      </RegexKeysColumn>
      <RegexKeysColumn
        v-model="item.key_black_regex"
        field="key_black_regex"
        :label="t('排除 Key')"
        @batch-edit="handleColumnBatchEdit">
      </RegexKeysColumn>
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisDSTHistoryJobModel from '@services/model/redis/redis-dst-history-job';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import RegexKeysColumn from '@views/db-manage/redis/common/toolbox-field/regex-keys-column/Index.vue';

  import AccessCodeColumn from '../common/AccessCodeColumn.vue';
  import ClusterInputColumn from '../common/ClusterInputColumn.vue';
  import RenderTargetCluster from '../common/TargetClusterColumn.vue';

  import ClusterTypeColumn, { ClusterType } from './components/ClusterTypeColumn.vue';

  interface Exposes {
    getValue: () => Promise<
      {
        dst_cluster: number;
        key_black_regex: string;
        key_white_regex: string;
        src_cluster: string;
        src_cluster_password: string;
        src_cluster_type: string;
      }[]
    >;
    resetTable: () => void;
    setTableByLocalStorage: (item: RedisDSTHistoryJobModel) => void;
    setTableByTicketClone: (infos: TicketModel<Redis.ClusterDataCopy>) => void;
  }

  interface IDataRow {
    dst_cluster: {
      domain: string;
      id: number;
    };
    key_black_regex: string[];
    key_white_regex: string[];
    src_cluster: string;
    src_cluster_password: string;
    src_cluster_type: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    dst_cluster: Object.assign(
      {
        domain: '',
        id: 0,
      },
      values.dst_cluster,
    ),
    key_black_regex: values?.key_black_regex || [],
    key_white_regex: values?.key_white_regex || ['*'],
    src_cluster: values?.src_cluster || '',
    src_cluster_password: values?.src_cluster_password || '',
    src_cluster_type: values?.src_cluster_type || ClusterType.REDIS_CLUSTER,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  const tableData = ref<IDataRow[]>([createRowData()]);

  const handleColumnBatchEdit = (value: string[], field: string) => {
    tableData.value.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    getValue: () =>
      editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          return tableData.value.map((tableItem) => ({
            dst_cluster: tableItem.dst_cluster.id,
            key_black_regex: tableItem.key_black_regex.join('\n'),
            key_white_regex: tableItem.key_white_regex.join('\n'),
            src_cluster: tableItem.src_cluster,
            src_cluster_password: tableItem.src_cluster_password,
            src_cluster_type: tableItem.src_cluster_type,
          }));
        }
        return [];
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
    setTableByLocalStorage: (item: RedisDSTHistoryJobModel) => {
      tableData.value = [
        createRowData({
          dst_cluster: {
            domain: item.dst_cluster,
            id: item.dst_cluster_id,
          },
          key_black_regex: item.key_black_regex === '' ? [] : item.key_black_regex.split('\n'),
          key_white_regex: item.key_white_regex === '' ? [] : item.key_white_regex.split('\n'),
          src_cluster: item.src_cluster,
          src_cluster_type: item.src_cluster_type,
        }),
      ];
    },
    setTableByTicketClone: (ticketDetail: TicketModel<Redis.ClusterDataCopy>) => {
      const { clusters, infos } = ticketDetail.details;
      tableData.value = infos.map((infoItem) =>
        createRowData({
          dst_cluster: {
            domain: clusters[infoItem.dst_cluster as number].immute_domain,
            id: infoItem.dst_cluster as number,
          },
          key_black_regex: infoItem.key_black_regex === '' ? [] : infoItem.key_black_regex.split('\n'),
          key_white_regex: infoItem.key_white_regex === '' ? [] : infoItem.key_white_regex.split('\n'),
          src_cluster: infoItem.src_cluster as string,
          src_cluster_type: infoItem.src_cluster_type,
        }),
      );
    },
  });
</script>
<style lang="less">
  .render-data {
    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
