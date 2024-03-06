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
  <div class="db-struct-target-cluster">
    <DbFormItem
      ref="formItemRef"
      :label="t('目标集群与构造设置')"
      property="clusterIds"
      required
      :rules="rules">
      <BkButton @click="handleShowClusterSelector">
        <DbIcon
          style="margin-right: 3px;"
          type="add" />
        <span style="font-size: 12px;">{{ t('添加目标集群') }}</span>
      </BkButton>
      <RenderData
        v-if="targetClusterList.length > 0"
        :cluster-type="clusterType"
        :is-backup-record-type="isBackupRecordType">
        <RenderDataRow
          v-for="(item, index) in targetClusterList"
          :key="item.id"
          ref="rowRefs"
          :cluster-type="clusterType"
          :counts="targetClusterList.length"
          :data="item"
          :index="index"
          :is-backup-record-type="isBackupRecordType"
          @remove="handleRemove"
          @struct-type-change="handleStructTypeChange" />
      </RenderData>
    </DbFormItem>
  </div>
  <ClusterSelector
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

  import ClusterSelector, {
    type TabItem,
  } from '@components/cluster-selector-new/Index.vue';

  import RenderData from './render-table/Index.vue';
  import RenderDataRow from './render-table/Row.vue';

  export interface IClusterData {
    id: number,
    cluster_name: string,
    status: string,
    master_domain: string,
    cluster_type: string
  }

  interface Props {
    clusterType: ClusterTypes,
    isBackupRecordType: boolean;
  }

  interface Emits {
    (e: 'change', value: MongoDBModel[]): void,
    (e: 'structTypeChange', value: string): void,
  }

  interface Exposes{
    getValue: () => Promise<Record<string, any>>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rowRefs = ref();

  const selectedClusters = shallowRef<{[key: string]: Array<MongoDBModel>}>({
    [ClusterTypes.MONGO_REPLICA_SET]: [],
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });


  const tabListConfig = computed(() => (props.clusterType === ClusterTypes.MONGO_REPLICA_SET ? {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      multiple: true,
    },
  } : {
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      multiple: false,
    },
  }) as unknown as Record<ClusterTypes, TabItem>);

  const rules = [
    {
      validator: (value: number[]) => value.length > 0,
      message: t('目标集群不能为空'),
      trigger: 'change',
    },
  ];

  const isShowClusterSelector = ref(false);
  const formItemRef = ref();
  const targetClusterList = ref<Array<MongoDBModel>>([]);

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handleStructTypeChange = (value: string) => {
    emits('structTypeChange', value);
  };

  const handleRemove = (index: number) => {
    const targetId = targetClusterList.value[index].id;
    targetClusterList.value.splice(index, 1);
    const clusterList = selectedClusters.value[props.clusterType];
    selectedClusters.value[props.clusterType] = clusterList.filter(item => item.id !== targetId);
    emits('change', targetClusterList.value);
  };

  const handelClusterChange = (selected: { [key: string]: Array<MongoDBModel> }) => {
    targetClusterList.value = selected[props.clusterType];
    selectedClusters.value = selected;
    emits('change', targetClusterList.value);
  };

  defineExpose<Exposes>({
    async getValue() {
      const infos = await Promise.all(rowRefs.value.map((item: {
        getValue: () => Promise<any>
      }) => item.getValue()));
      return infos;
    },
  });
</script>
<style lang="less">
  .db-struct-target-cluster {
    display: block;
    margin-bottom: 24px;

    .cluster-checking {
      height: 86px;
    }
  }
</style>
