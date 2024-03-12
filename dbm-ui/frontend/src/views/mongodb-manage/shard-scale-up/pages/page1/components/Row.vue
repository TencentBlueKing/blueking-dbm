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
  <tr>
    <td style="padding: 0">
      <RenderTargetCluster
        ref="clusterRef"
        :data="data.clusterName"
        :is-show-blur="data.isMongoReplicaSet"
        @input-finish="handleInputFinish">
        <template #blur>
          <RelatedClusters
            v-if="data.clusterName && relatedClusterDomains.length > 0"
            class="mb-10"
            :clusters="relatedClusterDomains" />
        </template>
      </RenderTargetCluster>
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.clusterTypeText"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.currentNodeNum"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderTargetNumber
        ref="targetNumRef"
        :current-node-num="data.currentNodeNum"
        :data="data.targetNum"
        :is-loading="data.isLoading" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderTargetCluster from '@views/mongodb-manage/components/edit-field/ClusterName.vue';
  import RelatedClusters from '@views/mongodb-manage/components/RelatedClusters.vue';

  import { random } from '@utils';

  import RenderTargetNumber from './RenderTargetNumber.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    clusterName: string;
    clusterId: number;
    clusterType: string;
    clusterTypeText: string;
    currentNodeNum: number;
    machineInstanceNum: number;
    shardNum: number;
    sepcId: number;
    isMongoReplicaSet: boolean;
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_ids: number[];
    add_shard_nodes: number;
    resource_spec: {
      shard_nodes: {
        spec_id: number;
        count: number;
      };
    };
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    clusterName: '',
    clusterId: 0,
    clusterType: '',
    clusterTypeText: '',
    currentNodeNum: 0,
    shardNum: 0,
    sepcId: 0,
    isMongoReplicaSet: false,
    machineInstanceNum: 0,
  });
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRelatedClustersByClusterIds } from '@services/source/mongodb';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const targetNumRef = ref<InstanceType<typeof RenderTargetNumber>>();
  const relatedClusterDomains = ref<string[]>([]);

  let relatedClusterIds: number[] = [];

  const { run: fetchRelatedClustersByClusterIds } = useRequest(getRelatedClustersByClusterIds, {
    manual: true,
    onSuccess(resultList) {
      if (resultList.length > 0) {
        const relatedClusters = resultList[0].related_clusters;
        if (relatedClusters.length > 0) {
          const domainList: string[] = [];
          const idList: number[] = [];
          relatedClusters.forEach((item) => {
            domainList.push(item.immute_domain);
            idList.push(item.id)
          })
          relatedClusterDomains.value = domainList;
          relatedClusterIds = idList;
        } else {
          relatedClusterDomains.value = [];
          relatedClusterIds = [];
        }
      }
    },
  });

  watch(
    () => props.data.isMongoReplicaSet,
    () => {
      if (props.data.isMongoReplicaSet) {
        // 副本集查关联集群
        fetchRelatedClustersByClusterIds({
          cluster_ids: [props.data.clusterId],
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value!.getValue();
      return targetNumRef.value!.getValue().then((nodeNum) => ({
        cluster_ids: props.data.isMongoReplicaSet
          ? [props.data.clusterId, ...relatedClusterIds]
          : [props.data.clusterId],
        add_shard_nodes: nodeNum - props.data.currentNodeNum, // 增加shard节点数
        current_shard_nodes_num: props.data.currentNodeNum, // 当前shard节点数
        machine_instance_num: props.data.machineInstanceNum, // 单机部署实例
        shard_num: props.data.shardNum, // 分片数
        resource_spec: {
          shard_nodes: {
            spec_id: props.data.sepcId,
            count: (props.data.shardNum / props.data.machineInstanceNum) * (nodeNum - props.data.currentNodeNum), // 分片数 / 每台机器的实例数 * 增加的节点数
          },
        },
      }));
    },
  });
</script>
