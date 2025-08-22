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
  <MachineReplace
    v-model="nodeInfoMap"
    v-model:is-show="isShow"
    :cluster-data="clusterData"
    :title="t('xx替换【name】', { title: 'ES', name: clusterData?.cluster_name })"
    @remove-node="handleRemoveNode"
    @submit="handleChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import EsModel from '@services/model/es/es';
  import EsMachineModel from '@services/model/es/es-machine';

  import { ClusterTypes } from '@common/const';

  import MachineReplace, { type TReplaceNode } from '@views/db-manage/common/machine-replace-es/Index.vue';

  interface Props {
    clusterData: EsModel;
    machineList?: EsMachineModel[];
  }

  interface Emits {
    (e: 'change'): void;
    (e: 'removeNode', bkHostId: number): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    machineList: () => [],
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<'client' | 'cold' | 'hot' | 'master', TReplaceNode>>({
    client: {
      clusterId: props.clusterData.id,
      hostList: [],
      label: t('Client 节点'),
      oldHostList: [],
      resourceSpec: {
        count: 0,
        instance_num: 1,
        spec_id: 0,
      },
      role: 'es_client',
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_client',
    },
    cold: {
      clusterId: props.clusterData.id,
      hostList: [],
      label: t('冷节点'),
      oldHostList: [],
      resourceSpec: {
        count: 0,
        instance_num: 1,
        spec_id: 0,
      },
      role: 'es_datanode_cold',
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_datanode',
    },
    hot: {
      clusterId: props.clusterData.id,
      hostList: [],
      label: t('热节点'),
      oldHostList: [],
      resourceSpec: {
        count: 0,
        instance_num: 1,
        spec_id: 0,
      },
      role: 'es_datanode_hot',
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_datanode',
    },
    master: {
      clusterId: props.clusterData.id,
      hostList: [],
      label: 'Master',
      oldHostList: [],
      resourceSpec: {
        count: 0,
        instance_num: 1,
        spec_id: 0,
      },
      role: 'es_master',
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_master',
    },
  });

  watch(
    () => props.machineList,
    () => {
      const hotList: TReplaceNode['oldHostList'] = [];
      const coldList: TReplaceNode['oldHostList'] = [];
      const clientList: TReplaceNode['oldHostList'] = [];
      const masterList: TReplaceNode['oldHostList'] = [];

      props.machineList.forEach((nodeItem) => {
        if (nodeItem.isHot) {
          hotList.push(nodeItem);
        } else if (nodeItem.isCold) {
          coldList.push(nodeItem);
        } else if (nodeItem.isClient) {
          clientList.push(nodeItem);
        } else if (nodeItem.isMaster) {
          masterList.push(nodeItem);
        }
      });

      nodeInfoMap.hot.oldHostList = hotList;
      nodeInfoMap.cold.oldHostList = coldList;
      nodeInfoMap.client.oldHostList = clientList;
      nodeInfoMap.master.oldHostList = masterList;
    },
    {
      immediate: true,
    },
  );

  const handleRemoveNode = (node: TReplaceNode['oldHostList'][number]) => {
    emits('removeNode', node.bk_host_id);
  };

  const handleChange = () => {
    emits('change');
  };
</script>
