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
  <MachineExpansion
    v-model="nodeInfoMap"
    v-model:is-show="isShow"
    :cluster-data="clusterData"
    :loading="isLoading"
    :title="t('xx扩容【name】', { title: 'Doris', name: clusterData.cluster_name })"
    @submit="handleChange" />
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import DorisMachineModel from '@services/model/doris/doris-machine';
  import { getDorisMachineList } from '@services/source/doris';

  import { ClusterTypes } from '@common/const';

  import MachineExpansion, { type TExpansionNode } from '@views/db-manage/common/machine-expansion/Index.vue';

  interface TDorisExpansionNode extends TExpansionNode {
    mutexNodeTypes: ('hot' | 'cold' | 'observer')[];
  }

  interface Props {
    clusterData: DorisModel;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const generateNodeInfo = (
    values: Pick<
      TDorisExpansionNode,
      'label' | 'role' | 'specMachineType' | 'tagText' | 'mutexNodeTypes' | 'showCount'
    >,
  ): TDorisExpansionNode => ({
    ...values,
    clusterId: props.clusterData.id,
    // targetDisk: 0,
    expansionDisk: 0,
    hostList: [],
    ipSource: 'resource_pool',
    originalHostList: [],
    resourceSpec: {
      count: 0,
      spec_id: 0,
    },
    specClusterType: ClusterTypes.DORIS,
    totalDisk: 0,
  });

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<string, TDorisExpansionNode>>({
    cold: generateNodeInfo({
      label: t('冷节点'),
      mutexNodeTypes: ['hot', 'observer'],
      role: 'doris_backend_cold',
      specMachineType: 'doris_backend',
      tagText: t('存储层'),
    }),
    hot: generateNodeInfo({
      label: t('热节点'),
      mutexNodeTypes: ['cold', 'observer'],
      role: 'doris_backend_hot',
      specMachineType: 'doris_backend',
      tagText: t('存储层'),
    }),
    observer: generateNodeInfo({
      label: t('Observer节点'),
      mutexNodeTypes: ['hot', 'cold'],
      role: 'doris_observer',
      showCount: true,
      specMachineType: 'doris_observer',
      tagText: t('接入层'),
    }),
  });

  const isLoading = ref(false);

  // 获取主机详情
  const fetchMachineDetail = () => {
    isLoading.value = true;

    getDorisMachineList({
      cluster_ids: String(props.clusterData.id),
      limit: -1,
      offset: 0,
    })
      .then((data) => {
        const hotOriginalHostList: DorisMachineModel[] = [];
        const coldOriginalHostList: DorisMachineModel[] = [];
        const observerOriginalHostList: DorisMachineModel[] = [];

        let hotDiskTotal = 0;
        let coldDiskTotal = 0;
        let observerDiskTotal = 0;

        data.results.forEach((hostItem) => {
          if (hostItem.isHot) {
            hotDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            hotOriginalHostList.push(hostItem);
          } else if (hostItem.isCold) {
            coldDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            coldOriginalHostList.push(hostItem);
          } else if (hostItem.isObserver) {
            observerDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            observerOriginalHostList.push(hostItem);
          }
        });

        nodeInfoMap.hot.totalDisk = hotDiskTotal;
        nodeInfoMap.hot.originalHostList = hotOriginalHostList;

        nodeInfoMap.cold.totalDisk = coldDiskTotal;
        nodeInfoMap.cold.originalHostList = coldOriginalHostList;

        nodeInfoMap.observer.totalDisk = observerDiskTotal;
        nodeInfoMap.observer.originalHostList = observerOriginalHostList;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchMachineDetail();

  const handleChange = () => {
    emits('change');
  };
</script>
