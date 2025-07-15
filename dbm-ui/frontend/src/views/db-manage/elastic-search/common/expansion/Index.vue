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
    :title="t('xx扩容【name】', { title: 'ES', name: clusterData.cluster_name })"
    @submit="handleChange" />
</template>
<script setup lang="tsx">
  import { reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import ESModel from '@services/model/es/es';
  import EsMachineModel from '@services/model/es/es-machine';
  import { getEsMachineList } from '@services/source/es';

  import { ClusterTypes } from '@common/const';

  import MachineExpansion, { type TExpansionNode } from '@views/db-manage/common/machine-expansion-es/Index.vue';

  interface Props {
    clusterData: ESModel;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<string, TExpansionNode>>({
    client: {
      clusterId: props.clusterData.id,
      expansionDisk: 0,
      hostList: [],
      ipSource: 'resource_pool',
      label: 'Client 节点',
      originalHostList: [],
      resourceSpec: {
        count: 0,
        instance_num: 1,
        spec_id: 0,
      },
      role: 'es_client',
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_client',
      tagText: t('接入层'),
      totalDisk: 0,
    },
    cold: {
      clusterId: props.clusterData.id,
      expansionDisk: 0,
      hostList: [],
      ipSource: 'resource_pool',
      label: t('冷节点'),
      originalHostList: [],
      resourceSpec: {
        count: 0,
        instance_num: 1,
        spec_id: 0,
      },
      role: 'es_datanode_cold',
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_datanode',
      tagText: t('存储层'),
      totalDisk: 0,
    },
    hot: {
      clusterId: props.clusterData.id,
      expansionDisk: 0,
      hostList: [],
      ipSource: 'resource_pool',
      label: '热节点',
      originalHostList: [],
      resourceSpec: {
        count: 0,
        instance_num: 1,
        spec_id: 0,
      },
      role: 'es_datanode_hot',
      specClusterType: ClusterTypes.ES,
      specMachineType: 'es_datanode',
      tagText: t('存储层'),
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);
  // 获取主机详情
  const fetchHostDetail = () => {
    isLoading.value = true;
    getEsMachineList({
      cluster_ids: String(props.clusterData.id),
      limit: -1,
      offset: 0,
    })
      .then((data) => {
        const hotOriginalHostList: EsMachineModel[] = [];
        const coldOriginalHostList: EsMachineModel[] = [];
        const clientOriginalHostList: EsMachineModel[] = [];

        let hotDiskTotal = 0;
        let coldDiskTotal = 0;
        let clientDiskTotal = 0;

        data.results.forEach((hostItem) => {
          if (hostItem.isHot) {
            hotDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            hotOriginalHostList.push(hostItem);
          }
          if (hostItem.isCold) {
            coldDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            coldOriginalHostList.push(hostItem);
          }
          if (hostItem.isClient) {
            clientDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            clientOriginalHostList.push(hostItem);
          }
        });

        nodeInfoMap.hot.totalDisk = hotDiskTotal;
        nodeInfoMap.hot.originalHostList = hotOriginalHostList;

        nodeInfoMap.cold.totalDisk = coldDiskTotal;
        nodeInfoMap.cold.originalHostList = coldOriginalHostList;

        nodeInfoMap.client.totalDisk = clientDiskTotal;
        nodeInfoMap.client.originalHostList = clientOriginalHostList;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  fetchHostDetail();

  const handleChange = () => {
    emits('change');
  };
</script>
