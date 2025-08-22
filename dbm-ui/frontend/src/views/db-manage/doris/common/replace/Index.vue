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
    :title="t('xx替换【name】', { title: 'Doris', name: clusterData?.cluster_name })"
    @remove-node="handleRemoveNode"
    @submit="handleChange" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import DorisMachineModel from '@services/model/doris/doris-machine';

  import { ClusterTypes } from '@common/const';

  import MachineReplace, { type TReplaceNode } from '@views/db-manage/common/machine-replace/Index.vue';

  interface Props {
    clusterData: DorisModel;
    machineList: DorisMachineModel[];
  }

  interface Emits {
    (e: 'change'): void;
    (e: 'removeNode', bkHostId: number): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const generateNodeInfo = (values: Pick<TReplaceNode, 'role' | 'specMachineType' | 'label'>): TReplaceNode => ({
    ...values,
    clusterId: props.clusterData.id,
    hostList: [],
    oldHostList: [],
    resourceSpec: {
      count: 0,
      spec_id: 0,
    },
    specClusterType: ClusterTypes.DORIS,
  });

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<'cold' | 'hot' | 'observer' | 'follower', TReplaceNode>>({
    cold: generateNodeInfo({
      label: t('冷节点'),
      role: 'doris_backend_cold',
      specMachineType: 'doris_backend',
    }),
    follower: generateNodeInfo({
      label: 'Follower',
      role: 'doris_follower',
      specMachineType: 'doris_follower',
    }),
    hot: generateNodeInfo({
      label: t('热节点'),
      role: 'doris_backend_hot',

      specMachineType: 'doris_backend',
    }),
    observer: generateNodeInfo({
      label: 'Observer',
      role: 'doris_observer',
      specMachineType: 'doris_observer',
    }),
  });

  watch(
    () => props.machineList,
    () => {
      const hotList: TReplaceNode['oldHostList'] = [];
      const coldList: TReplaceNode['oldHostList'] = [];
      const observerList: TReplaceNode['oldHostList'] = [];
      const followerList: TReplaceNode['oldHostList'] = [];

      props.machineList.forEach((machineItem) => {
        if (machineItem.isHot) {
          hotList.push(machineItem);
        } else if (machineItem.isCold) {
          coldList.push(machineItem);
        } else if (machineItem.isObserver) {
          observerList.push(machineItem);
        } else if (machineItem.isFollower) {
          followerList.push(machineItem);
        }
      });

      nodeInfoMap.hot.oldHostList = hotList;
      nodeInfoMap.cold.oldHostList = coldList;
      nodeInfoMap.observer.oldHostList = observerList;
      nodeInfoMap.follower.oldHostList = followerList;
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
