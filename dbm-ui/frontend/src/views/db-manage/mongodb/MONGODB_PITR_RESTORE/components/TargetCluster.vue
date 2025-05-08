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
  <BkFormItem
    :label="t('集群类型')"
    required>
    <BkRadioGroup
      v-model="clusterType"
      style="width: 400px"
      type="card"
      @change="handleChange">
      <BkRadioButton :label="ClusterTypes.MONGO_REPLICA_SET">
        {{ t('副本集集群') }}
      </BkRadioButton>
      <BkRadioButton :label="ClusterTypes.MONGO_SHARED_CLUSTER">
        {{ t('分片集群') }}
      </BkRadioButton>
    </BkRadioGroup>
  </BkFormItem>
  <BkFormItem
    :label="t('目标集群与构造设置')"
    required>
    <BkButton @click="handleShowClusterSelector">
      <DbIcon
        style="margin-right: 3px"
        type="add" />
      <span style="font-size: 12px">{{ t('添加目标集群') }}</span>
    </BkButton>
    <EditableTable
      v-if="tableData.length"
      ref="table"
      class="mt-20"
      :model="tableData"
      :rules="rules">
      <EditableRow
        v-for="(item, index) in tableData"
        :key="index">
        <EditableColumn
          field="cluster.master_domain"
          :label="t('集群')"
          required>
          <EditableBlock v-model="item.cluster.master_domain" />
        </EditableColumn>
        <EditableColumn
          field="cluster.major_version"
          :label="t('版本')"
          :width="150">
          <EditableBlock v-model="item.cluster.major_version" />
        </EditableColumn>
        <RollbackTimeColumn
          v-model="item.rollback_time"
          @batch-edit="handleBatchEdit" />
        <EditableColumn
          fixed="right"
          :label="t('操作')"
          :width="100">
          <BkButton
            class="ml-16"
            text
            theme="primary"
            @click="() => handleRemove(index, item.cluster.id)">
            {{ t('删除') }}
          </BkButton>
        </EditableColumn>
      </EditableRow>
    </EditableTable>
  </BkFormItem>
  <ClusterSelector
    :key="clusterType"
    v-model:is-show="isShowClusterSelector"
    :cluster-types="[clusterType]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongoDBModel from '@services/model/mongodb/mongodb';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector, { type TabItem } from '@components/cluster-selector/Index.vue';

  import RollbackTimeColumn from './RollbackTimeColumn.vue';

  export interface RowData {
    cluster: MongoDBModel;
    rollback_time: string;
  }

  interface Exposes {
    validate(): Promise<boolean>;
  }

  const tableData = defineModel<RowData[]>({
    default: [],
  });

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const isShowClusterSelector = ref(false);
  const clusterType = ref(ClusterTypes.MONGO_REPLICA_SET);
  const selectedClusters = shallowRef<{ [key: string]: Array<MongoDBModel> }>({
    [ClusterTypes.MONGO_REPLICA_SET]: [],
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  const tabListConfig = {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      multiple: true,
      name: t('副本集集群'),
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      multiple: false,
      name: t('分片集群'),
    },
  } as Record<ClusterTypes, TabItem>;

  const rules = {
    'cluster.major_version': [
      {
        message: t('版本要求一致'),
        trigger: 'blur',
        validator: (value: string) => {
          return value === tableData.value[0].cluster.major_version;
        },
      },
    ],
  };

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: { [key: string]: Array<MongoDBModel> }) => {
    selectedClusters.value = selected;
    tableData.value = selected[clusterType.value].map((item) => ({
      cluster: item,
      rollback_time: '',
    }));
  };

  const handleRemove = (rowIndex: number, clusterId: number) => {
    tableData.value.splice(rowIndex, 1);
    const clusterList = selectedClusters.value[clusterType.value];
    selectedClusters.value[clusterType.value] = clusterList.filter((item) => item.id !== clusterId);
  };

  const handleChange = () => {
    selectedClusters.value = {
      [ClusterTypes.MONGO_REPLICA_SET]: [],
      [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
    };
    tableData.value = [];
  };

  const handleBatchEdit = (value: string | string[], field: string) => {
    tableData.value.forEach((item) => {
      Object.assign(item, {
        [field]: value,
      });
    });
  };

  defineExpose<Exposes>({
    validate() {
      return tableRef.value!.validate();
    },
  });
</script>
