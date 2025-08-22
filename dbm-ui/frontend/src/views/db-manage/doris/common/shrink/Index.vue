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
  <MachineShrink
    v-model="nodeInfoMap"
    v-model:is-show="isShow"
    :data="clusterData"
    :loading="isLoading"
    :title="t('xx缩容【name】', { title: 'Doris', name: clusterData?.cluster_name })"
    @submit="handleChange" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import DorisMachineModel from '@services/model/doris/doris-machine';
  import { getDorisNodeList } from '@services/source/doris';

  import MachineShrink, { type TShrinkNode } from '@views/db-manage/common/machine-shrink/Index.vue';

  interface Props {
    clusterData: DorisModel;
    machineList?: DorisMachineModel[];
  }

  type Emits = (e: 'change') => void;

  const props = withDefaults(defineProps<Props>(), {
    machineList: () => [],
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const generateNodeInfo = (values: Pick<TShrinkNode, 'label' | 'minHost' | 'tagText'>): TShrinkNode => ({
    ...values,
    hostList: [],
    originalNodeList: [],
    // targetDisk: 0,
    shrinkDisk: 0,
    totalDisk: 0,
  });

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<'cold' | 'hot' | 'observer', TShrinkNode>>({
    cold: generateNodeInfo({
      label: t('冷节点'),
      minHost: 0,
      tagText: t('存储层'),
    }),
    hot: generateNodeInfo({
      label: t('热节点'),
      minHost: 0,
      tagText: t('存储层'),
    }),
    observer: generateNodeInfo({
      label: 'Observer',
      minHost: 0,
      tagText: t('接入层'),
    }),
  });

  const isLoading = ref(false);

  const fetchListNode = () => {
    const hotOriginalNodeList: TShrinkNode['originalNodeList'] = [];
    const coldOriginalNodeList: TShrinkNode['originalNodeList'] = [];
    const observerOriginalNodeList: TShrinkNode['originalNodeList'] = [];

    isLoading.value = true;
    getDorisNodeList({
      bk_biz_id: props.clusterData.bk_biz_id,
      cluster_id: props.clusterData.id,
      no_limit: 1,
    })
      .then((data) => {
        let hotDiskTotal = 0;
        let coldDiskTotal = 0;
        let observerDiskTotal = 0;

        data.results.forEach((nodeItem) => {
          if (nodeItem.isHot) {
            hotDiskTotal += nodeItem.disk;
            hotOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isCold) {
            coldDiskTotal += nodeItem.disk;
            coldOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isObserver) {
            observerDiskTotal += nodeItem.disk;
            observerOriginalNodeList.push(nodeItem);
          }
        });

        nodeInfoMap.hot.originalNodeList = hotOriginalNodeList;
        nodeInfoMap.hot.totalDisk = hotDiskTotal;

        nodeInfoMap.cold.originalNodeList = coldOriginalNodeList;
        nodeInfoMap.cold.totalDisk = coldDiskTotal;

        nodeInfoMap.observer.originalNodeList = observerOriginalNodeList;
        nodeInfoMap.observer.totalDisk = observerDiskTotal;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchListNode();

  // 默认选中的缩容节点
  watch(
    () => props.machineList,
    () => {
      const hotList: TShrinkNode['hostList'] = [];
      const coldList: TShrinkNode['hostList'] = [];
      const observerList: TShrinkNode['hostList'] = [];

      let hotShrinkDisk = 0;
      let coldShrinkDisk = 0;
      let observerShrinkDisk = 0;

      props.machineList.forEach((machineItem) => {
        const machineDisk = machineItem.host_info?.bk_disk || 0;
        const machineHost = {
          alive: machineItem.host_info?.alive || 0,
          bk_cloud_id: machineItem.bk_cloud_id,
          bk_disk: machineDisk,
          bk_host_id: machineItem.bk_host_id,
          ip: machineItem.ip,
        };
        if (machineItem.isHot) {
          hotShrinkDisk += machineDisk;
          hotList.push(machineHost);
        } else if (machineItem.isCold) {
          coldShrinkDisk += machineDisk;
          coldList.push(machineHost);
        } else if (machineItem.isObserver) {
          observerShrinkDisk += machineDisk;
          observerList.push(machineHost);
        }
      });
      nodeInfoMap.hot.hostList = hotList;
      nodeInfoMap.hot.shrinkDisk = hotShrinkDisk;
      nodeInfoMap.cold.hostList = coldList;
      nodeInfoMap.cold.shrinkDisk = coldShrinkDisk;
      nodeInfoMap.observer.hostList = observerList;
      nodeInfoMap.observer.shrinkDisk = observerShrinkDisk;
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    emits('change');
  };
</script>
