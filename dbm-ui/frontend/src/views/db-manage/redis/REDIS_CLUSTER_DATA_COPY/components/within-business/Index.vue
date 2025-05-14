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
      <ClusterColumn
        v-model="item.cluster"
        :label="t('源集群')"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @batch-edit="handleClusterBatchEdit" />
      <EditableColumn
        :label="t('架构版本')"
        :width="200">
        <EditableBlock
          v-model="item.cluster.cluster_type_name"
          :placeholder="t('选择集群后自动生成')">
        </EditableBlock>
      </EditableColumn>
      <RenderTargetCluster
        v-model="item.dst_cluster"
        :src-cluster-id="item.cluster.id">
      </RenderTargetCluster>
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

  import RedisModel from '@services/model/redis/redis';
  import RedisDSTHistoryJobModel from '@services/model/redis/redis-dst-history-job';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { ClusterTypes } from '@common/const';

  import { type TabConfig } from '@components/cluster-selector/Index.vue';

  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';
  import RegexKeysColumn from '@views/db-manage/redis/common/toolbox-field/regex-keys-column/Index.vue';

  import RenderTargetCluster from '../common/TargetClusterColumn.vue';

  interface Exposes {
    getValue: () => Promise<
      {
        dst_cluster: number;
        key_black_regex: string;
        key_white_regex: string;
        src_cluster: number;
      }[]
    >;
    resetTable: () => void;
    setTableByLocalStorage: (item: RedisDSTHistoryJobModel) => void;
    setTableByTicketClone: (infos: TicketModel<Redis.ClusterDataCopy>) => void;
  }

  interface IDataRow {
    cluster: {
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
    dst_cluster: number;
    key_black_regex: string[];
    key_white_regex: string[];
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      values.cluster,
    ),
    dst_cluster: values?.dst_cluster || 0,
    key_black_regex: values?.key_black_regex || [],
    key_white_regex: values?.key_white_regex || ['*'],
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      columnStatusFilter: (data: RedisModel) =>
        data.redis_slave.filter((item) => item.status !== 'running').length === 0,
      disabledRowConfig: [
        {
          handler: (data: RedisModel) => data.redis_slave.filter((item) => item.status !== 'running').length > 0,
          tip: t('slave 状态异常，无法选择'),
        },
      ],
    },
  } as unknown as Record<string, TabConfig>;

  const tableData = ref<IDataRow[]>([createRowData()]);

  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (list: RedisModel[]) => {
    const newList: IDataRow[] = [];
    list.forEach((item) => {
      const { master_domain: domain } = item;
      if (!selectedMap.value[domain]) {
        newList.push(
          createRowData({
            cluster: {
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
            },
          }),
        );
      }
    });

    tableData.value = [...(selected.value.length ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

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
            dst_cluster: tableItem.dst_cluster,
            key_black_regex: tableItem.key_black_regex.join('\n'),
            key_white_regex: tableItem.key_white_regex.join('\n'),
            src_cluster: tableItem.cluster.id,
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
          cluster: {
            master_domain: item.src_cluster ? item.src_cluster.split(':')[0] : '',
          } as IDataRow['cluster'],
          dst_cluster: item.dst_cluster_id,
          key_black_regex: item.key_black_regex === '' ? [] : item.key_black_regex.split('\n'),
          key_white_regex: item.key_white_regex === '' ? [] : item.key_white_regex.split('\n'),
        }),
      ];
    },
    setTableByTicketClone: (ticketDetail: TicketModel<Redis.ClusterDataCopy>) => {
      const { clusters, infos } = ticketDetail.details;
      tableData.value = infos.map((infoItem) =>
        createRowData({
          cluster: { master_domain: clusters[infoItem.src_cluster as number].immute_domain } as IDataRow['cluster'],
          dst_cluster: infoItem.dst_cluster as number,
          key_black_regex: infoItem.key_black_regex === '' ? [] : infoItem.key_black_regex.split('\n'),
          key_white_regex: infoItem.key_white_regex === '' ? [] : infoItem.key_white_regex.split('\n'),
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
