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
  <div>
    <BatchInput
      :config="batchInputConfig"
      @change="handleBatchInput" />
    <EditableTable
      :key="tableKey"
      ref="editableTable"
      class="mt-16 mb-16"
      :model="tableData">
      <EditableRow
        v-for="(item, index) in tableData"
        :key="index">
        <ClusterColumn
          v-model="item.cluster"
          :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
          field="cluster.master_domain"
          :label="t('目标集群')"
          :selected="selected"
          @batch-edit="handleClusterBatchEdit" />
        <EditableColumn
          :label="t('当前分片数')"
          readonly
          :width="120">
          <EditableBlock :placeholder="t('自动生成')">
            {{ item.cluster.id ? item.cluster.shard_num : '' }}
          </EditableBlock>
        </EditableColumn>
        <ShardSelectColumn
          v-model="item.shard_names"
          :cluster-id="item.cluster.id" />
        <EditableColumn
          :append-rules="finalShardRules"
          field="final_shard_num"
          :label="t('最终分片数')"
          readonly
          :width="120">
          <EditableBlock :placeholder="t('自动生成')">
            {{ getFinalShardNum(item) }}
          </EditableBlock>
        </EditableColumn>
        <OperationColumn
          :create-row-method="createRowData"
          :table-data="tableData" />
      </EditableRow>
    </EditableTable>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import type { Mongodb } from '@services/model/ticket/ticket';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import ShardSelectColumn from '../shard-select-column/Index.vue';

  interface IDataRow {
    cluster: {
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
      shard_num: number;
    };
    shard_names: string[];
  }

  interface Exposes {
    getValue(): {
      cluster_id: number;
      reduce_mode: 'by_shard_names';
      shard_names: string[];
    }[];
    reset(): void;
    validate(): Promise<boolean>;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
        shard_num: 0,
      },
      values.cluster,
    ),
    shard_names: values.shard_names || [],
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  const batchInputConfig = [
    {
      case: 'mongodb.test.dba.db',
      key: 'domain',
      label: t('目标集群'),
    },
  ];

  const tableKey = ref(random());

  const tableData = reactive([createRowData()]);

  // 克隆单回显：在回调里取本模式需要的信息，还原指定分片模式的行
  useTicketDetail<Mongodb.ReduceShard>(TicketTypes.MONGODB_REDUCE_SHARD, {
    onSuccess(ticketDetail) {
      const { clusters, infos } = ticketDetail.details;
      const rows = infos
        .filter((item) => item.reduce_mode === 'by_shard_names')
        .map((item) =>
          createRowData({
            cluster: {
              master_domain: clusters[item.cluster_id]?.immute_domain || '',
            } as IDataRow['cluster'],
            shard_names: item.shard_names || [],
          }),
        );
      if (rows.length) {
        tableKey.value = random();
        Object.assign(tableData, [...rows]);
      }
    },
  });

  const selected = computed(() => tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  // 最终分片数演算校验：当前 - 已选数，不能为 0（value 为演算展示值，判定基于 rowData）
  const finalShardRules = [
    {
      message: t('最终分片数不能为0'),
      trigger: 'change',
      validator: (_value: number, { rowData }: { rowData: IDataRow }) => {
        if (!rowData.cluster.id || !rowData.cluster.shard_num) {
          return true;
        }
        return rowData.cluster.shard_num - rowData.shard_names.length >= 1;
      },
    },
  ];

  // 最终分片数演算：当前 - 已选数；当前分片数未带出时显示 --
  const getFinalShardNum = (item: IDataRow) => {
    if (!item.cluster.id || !item.cluster.shard_num) {
      return '';
    }
    const finalNum = item.cluster.shard_num - item.shard_names.length;
    return Number.isInteger(finalNum) && finalNum >= 0 ? finalNum : '--';
  };

  const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              master_domain: item.master_domain,
            } as IDataRow['cluster'],
          }),
        );
      }
    });
    Object.assign(tableData, [...(selected.value.length ? tableData : []), ...newList]);
  };

  const handleBatchInput = (data: Record<string, string>[], isClear: boolean) => {
    const dataList = data.map((item) =>
      createRowData({
        cluster: {
          master_domain: item.domain,
        } as IDataRow['cluster'],
      }),
    );

    if (isClear) {
      tableKey.value = random();
      Object.assign(tableData, [...dataList]);
    } else {
      Object.assign(tableData, [...(selected.value.length ? tableData : []), ...dataList]);
    }
  };

  defineExpose<Exposes>({
    getValue() {
      return tableData.map((tableRow) => ({
        cluster_id: tableRow.cluster.id,
        current_shard_num: tableRow.cluster.shard_num,
        reduce_mode: 'by_shard_names' as const,
        shard_names: tableRow.shard_names,
      }));
    },
    reset() {
      Object.assign(tableData, [createRowData()]);
      tableKey.value = random();
    },
    validate() {
      return editableTableRef.value!.validate().then(() => true);
    },
  });
</script>
