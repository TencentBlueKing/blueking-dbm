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
    :title="t('xx缩容【name】', { title: 'Pulsar', name: clusterData?.cluster_name })"
    @submit="handleChange" />
</template>
<script setup lang="tsx">
  import { reactive, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import PulsarModel from '@services/model/pulsar/pulsar';
  import PulsarMachineModel from '@services/model/pulsar/pulsar-machine';
  import { getPulsarNodeList } from '@services/source/pulsar';

  import MachineShrink, { type TShrinkNode } from '@views/db-manage/common/machine-shrink/Index.vue';

  interface Props {
    clusterData: PulsarModel;
    machineList?: PulsarMachineModel[];
  }

  type Emits = (e: 'change') => void;

  const props = withDefaults(defineProps<Props>(), {
    machineList: () => [],
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<string, TShrinkNode>>({
    bookkeeper: {
      hostList: [],
      label: 'Bookkeeper',
      minHost: 2,
      originalNodeList: [],
      // targetDisk: 0,
      shrinkDisk: 0,
      tagText: t('存储层'),
      totalDisk: 0,
    },
    broker: {
      hostList: [],
      label: 'Broker',
      minHost: 1,
      originalNodeList: [],
      // 缩容后的目标容量
      // targetDisk: 0,
      // 实际选择的缩容主机容量
      shrinkDisk: 0,
      tagText: t('接入层'),
      // 当前主机总容量
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);
  const nodeType = ref('broker');

  const fetchListNode = () => {
    const bookkeeperOriginalNodeList: TShrinkNode['originalNodeList'] = [];
    const brokerOriginalNodeList: TShrinkNode['originalNodeList'] = [];

    isLoading.value = true;
    getPulsarNodeList({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.clusterData.id,
      no_limit: 1,
    })
      .then((data) => {
        let bookkeeperDiskTotal = 0;
        let brokerDiskTotal = 0;

        data.results.forEach((nodeItem) => {
          if (nodeItem.isBookkeeper) {
            bookkeeperDiskTotal += nodeItem.disk;
            bookkeeperOriginalNodeList.push(nodeItem);
          } else if (nodeItem.isBroker) {
            brokerDiskTotal += nodeItem.disk;
            brokerOriginalNodeList.push(nodeItem);
          }
        });

        nodeInfoMap.bookkeeper.originalNodeList = bookkeeperOriginalNodeList;
        nodeInfoMap.bookkeeper.totalDisk = bookkeeperDiskTotal;

        nodeInfoMap.broker.originalNodeList = brokerOriginalNodeList;
        nodeInfoMap.broker.totalDisk = brokerDiskTotal;
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
      const bookkeeperHostList: TShrinkNode['hostList'] = [];
      const brokerHostList: TShrinkNode['hostList'] = [];

      let bookkeeperShrinkDisk = 0;
      let brokerShrinkDisk = 0;

      props.machineList.forEach((machineItem) => {
        if (machineItem.isBookkeeper) {
          bookkeeperShrinkDisk += machineItem.host_info?.bk_disk || 0;
          bookkeeperHostList.push({
            alive: machineItem.host_info?.alive || 0,
            bk_cloud_id: machineItem.bk_cloud_id,
            bk_disk: machineItem.host_info.bk_disk,
            bk_host_id: machineItem.bk_host_id,
            ip: machineItem.ip,
          });
        } else if (machineItem.isBroker) {
          brokerShrinkDisk += machineItem.host_info?.bk_disk || 0;
          brokerHostList.push({
            alive: machineItem.host_info?.alive || 0,
            bk_cloud_id: machineItem.bk_cloud_id,
            bk_disk: machineItem.host_info.bk_disk,
            bk_host_id: machineItem.bk_host_id,
            ip: machineItem.ip,
          });
        }
      });
      nodeInfoMap.bookkeeper.hostList = bookkeeperHostList;
      nodeInfoMap.bookkeeper.shrinkDisk = bookkeeperShrinkDisk;
      nodeInfoMap.broker.hostList = brokerHostList;
      nodeInfoMap.broker.shrinkDisk = brokerShrinkDisk;

      if (bookkeeperHostList.length) {
        nodeType.value = 'bookkeeper';
      } else if (brokerHostList.length) {
        nodeType.value = 'broker';
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
