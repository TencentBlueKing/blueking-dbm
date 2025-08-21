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
    :title="t('xx缩容【name】', { title: 'ES', name: clusterData?.cluster_name })"
    @submit="handleChange" />
</template>
<script setup lang="tsx">
  import { reactive, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import EsModel from '@services/model/es/es';
  import EsMachineModel from '@services/model/es/es-machine';
  import { getEsNodeList } from '@services/source/es';

  import MachineShrink, { type TShrinkNode } from '@views/db-manage/common/machine-shrink/Index.vue';

  interface Props {
    clusterData: EsModel;
    machineList?: EsMachineModel[];
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
    client: {
      hostList: [],
      label: 'Client',
      minHost: 0,
      originalNodeList: [],
      shrinkDisk: 0,
      tagText: t('接入层'),
      totalDisk: 0,
    },
    cold: {
      hostList: [],
      label: t('冷节点'),
      minHost: 0,
      originalNodeList: [],
      shrinkDisk: 0,
      tagText: t('存储层'),
      totalDisk: 0,
    },
    hot: {
      hostList: [],
      label: t('热节点'),
      minHost: 0,
      originalNodeList: [],
      shrinkDisk: 0,
      tagText: t('存储层'),
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);
  const nodeType = ref('cold');

  const fetchListNode = () => {
    const hotOriginalList: TShrinkNode['originalNodeList'] = [];
    const coldOriginalList: TShrinkNode['originalNodeList'] = [];
    const clientOriginalList: TShrinkNode['originalNodeList'] = [];

    isLoading.value = true;
    getEsNodeList({
      bk_biz_id: props.clusterData.bk_biz_id,
      cluster_id: props.clusterData.id,
      no_limit: 1,
    })
      .then((data) => {
        let hotDiskTotal = 0;
        let coldDiskTotal = 0;
        let clientDiskTotal = 0;

        data.results.forEach((nodeItem) => {
          if (nodeItem.isHot) {
            hotDiskTotal += nodeItem.disk;
            hotOriginalList.push(nodeItem);
          } else if (nodeItem.isCold) {
            coldDiskTotal += nodeItem.disk;
            coldOriginalList.push(nodeItem);
          } else if (nodeItem.isClient) {
            clientDiskTotal += nodeItem.disk;
            clientOriginalList.push(nodeItem);
          }
        });

        nodeInfoMap.hot.originalNodeList = hotOriginalList;
        nodeInfoMap.hot.totalDisk = hotDiskTotal;

        nodeInfoMap.cold.originalNodeList = coldOriginalList;
        nodeInfoMap.cold.totalDisk = coldDiskTotal;

        nodeInfoMap.client.originalNodeList = clientOriginalList;
        nodeInfoMap.client.totalDisk = clientDiskTotal;
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
      const hotHostList: TShrinkNode['hostList'] = [];
      const coldHostList: TShrinkNode['hostList'] = [];
      const clientHostList: TShrinkNode['hostList'] = [];

      let hotShrinkDisk = 0;
      let coldShrinkDisk = 0;
      let clientShrinkDisk = 0;

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
          hotHostList.push(machineHost);
        } else if (machineItem.isCold) {
          coldShrinkDisk += machineDisk;
          coldHostList.push(machineHost);
        } else if (machineItem.isClient) {
          clientShrinkDisk += machineDisk;
          clientHostList.push(machineHost);
        }
      });
      nodeInfoMap.hot.hostList = hotHostList;
      nodeInfoMap.hot.shrinkDisk = hotShrinkDisk;
      nodeInfoMap.cold.hostList = coldHostList;
      nodeInfoMap.cold.shrinkDisk = coldShrinkDisk;
      nodeInfoMap.client.hostList = clientHostList;
      nodeInfoMap.client.shrinkDisk = clientShrinkDisk;

      if (coldHostList.length) {
        nodeType.value = 'cold';
      } else if (hotHostList.length) {
        nodeType.value = 'hot';
      } else if (clientHostList.length) {
        nodeType.value = 'client';
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
