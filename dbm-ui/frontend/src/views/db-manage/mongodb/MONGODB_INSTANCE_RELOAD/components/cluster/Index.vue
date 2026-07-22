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
      ref="tableRef"
      class="mt-16 mb-20"
      :model="tableData">
      <EditableRow
        v-for="(item, index) in tableData"
        :key="index">
        <ClusterColumn
          v-model="item.cluster"
          :cluster-types="[ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER]"
          field="cluster.master_domain"
          :label="t('目标集群')"
          :selected="selectedClusters"
          @batch-edit="handleBatchEdit" />
        <EditableColumn
          :label="t('集群类型')"
          :min-width="150"
          readonly>
          <EditableBlock
            v-model="item.cluster.cluster_type_name"
            :placeholder="t('输入集群后自动生成')" />
        </EditableColumn>
        <OperationColumn
          v-model:table-data="tableData"
          :create-row-method="createRow" />
      </EditableRow>
    </EditableTable>
  </div>
</template>

<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { type Mongodb } from '@services/model/ticket/ticket';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';
  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  interface ClusterRowData {
    cluster: {
      cluster_type: ClusterTypes;
      cluster_type_name: string;
      id: number;
      master_domain: string;
    };
  }

  interface Exposes {
    getValue: () => Mongodb.InstanceReload['infos'];
    validate: () => Promise<boolean>;
  }

  const { t } = useI18n();

  const tableRef = useTemplateRef('tableRef');

  // 单据详情回显
  useTicketDetail<Mongodb.InstanceReload>(TicketTypes.MONGODB_INSTANCE_RELOAD, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, target_select_mode: targetSelectMode } = details;
      const infos = details.infos as { cluster_id: number }[];

      if (targetSelectMode === 'cluster') {
        tableData.value = infos.map((item) =>
          createRow({ cluster: { master_domain: clusters[item.cluster_id].immute_domain } }),
        );
      }
    },
  });

  const batchInputConfig = [
    {
      case: 'mongo.test.dba.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
  ];

  const createRow = (data: DeepPartial<ClusterRowData> = {}) => ({
    cluster: Object.assign(
      {
        cluster_type: '' as ClusterTypes,
        cluster_type_name: '',
        id: 0,
        master_domain: '',
      },
      data.cluster,
    ),
  });

  const tableData = ref([createRow()]);
  const tableKey = ref(random());

  const selectedClusters = computed(() =>
    tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster),
  );
  const selectedClustersMap = computed(() =>
    Object.fromEntries(selectedClusters.value.map((cur) => [cur.master_domain, true])),
  );

  const handleBatchEdit = (list: MongodbModel[]) => {
    const dataList = list.reduce<ClusterRowData[]>((acc, item) => {
      if (!selectedClustersMap.value[item.master_domain]) {
        acc.push(createRow({ cluster: { master_domain: item.master_domain } }));
      }
      return acc;
    }, []);
    tableData.value = [...(selectedClusters.value.length ? tableData.value : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<ClusterRowData[]>((acc, item) => {
      acc.push(createRow({ cluster: { master_domain: item.master_domain } }));
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(tableData.value[0]?.cluster.id ? tableData.value : []), ...dataList];
    }
  };

  defineExpose<Exposes>({
    getValue: () =>
      tableData.value.map((item) => ({
        cluster_id: item.cluster.id,
      })),
    validate: () => tableRef.value!.validate(),
  });
</script>
