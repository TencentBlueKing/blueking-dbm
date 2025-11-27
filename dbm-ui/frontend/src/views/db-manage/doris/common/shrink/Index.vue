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
    :title="t('xx缩容【name】', { title: 'Doris', name: clusterData?.master_domain })"
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

  const getInitInfo = (): Record<'warm' | 'hot' | 'observer', TShrinkNode> => ({
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
    warm: generateNodeInfo({
      label: t('温节点'),
      minHost: 0,
      tagText: t('存储层'),
    }),
  });

  const nodeInfoMap = reactive(getInitInfo());
  const isLoading = ref(false);

  const fetchListNode = () => {
    const hotOriginalNodeList: TShrinkNode['originalNodeList'] = [];
    const warmOriginalNodeList: TShrinkNode['originalNodeList'] = [];
    const observerOriginalNodeList: TShrinkNode['originalNodeList'] = [];

    isLoading.value = true;
    getDorisNodeList({
      bk_biz_id: props.clusterData.bk_biz_id,
      cluster_id: props.clusterData.id,
      no_limit: 1,
    })
      .then((data) => {
        let hotDiskTotal = 0;
        let warmDiskTotal = 0;
        let observerDiskTotal = 0;

        data.results.forEach((nodeItem) => {
          if (nodeItem.isHot) {
            hotDiskTotal += nodeItem.disk;
            hotOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isWarm) {
            warmDiskTotal += nodeItem.disk;
            warmOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isObserver) {
            observerDiskTotal += nodeItem.disk;
            observerOriginalNodeList.push(nodeItem);
          }
        });

        nodeInfoMap.hot.originalNodeList = hotOriginalNodeList;
        nodeInfoMap.hot.totalDisk = hotDiskTotal;

        nodeInfoMap.warm.originalNodeList = warmOriginalNodeList;
        nodeInfoMap.warm.totalDisk = warmDiskTotal;

        nodeInfoMap.observer.originalNodeList = observerOriginalNodeList;
        nodeInfoMap.observer.totalDisk = observerDiskTotal;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  // 默认选中的缩容节点
  const setInitShrinkNodes = () => {
    const hotList: TShrinkNode['hostList'] = [];
    const warmList: TShrinkNode['hostList'] = [];
    const observerList: TShrinkNode['hostList'] = [];

    let hotShrinkDisk = 0;
    let warmShrinkDisk = 0;
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
      } else if (machineItem.isWarm) {
        warmShrinkDisk += machineDisk;
        warmList.push(machineHost);
      } else if (machineItem.isObserver) {
        observerShrinkDisk += machineDisk;
        observerList.push(machineHost);
      }
    });
    nodeInfoMap.hot.hostList = hotList;
    nodeInfoMap.hot.shrinkDisk = hotShrinkDisk;
    nodeInfoMap.warm.hostList = warmList;
    nodeInfoMap.warm.shrinkDisk = warmShrinkDisk;
    nodeInfoMap.observer.hostList = observerList;
    nodeInfoMap.observer.shrinkDisk = observerShrinkDisk;
  };

  watch(
    isShow,
    () => {
      if (isShow.value) {
        Object.assign(nodeInfoMap, getInitInfo());
        setInitShrinkNodes();
        fetchListNode();
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    emits('change');
  };
</script>
