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
    :title="t('xx扩容【name】', { title: 'HDFS', name: clusterData.cluster_name })"
    @submit="handleChange" />
</template>
<script setup lang="tsx">
  import { reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import HdfsModel from '@services/model/hdfs/hdfs';
  import HdfsMachineModel from '@services/model/hdfs/hdfs-machine';
  import { getHdfsMachineList } from '@services/source/hdfs';

  import { ClusterTypes } from '@common/const';

  import MachineExpansion, { type TExpansionNode } from '@views/db-manage/common/machine-expansion/Index.vue';

  interface Props {
    clusterData: HdfsModel;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });
  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<string, TExpansionNode>>({
    datanode: {
      clusterId: props.clusterData.id,
      // targetDisk: 0,
      expansionDisk: 0,
      hostList: [],
      ipSource: 'resource_pool',
      label: 'Datanode',
      originalHostList: [],
      resourceSpec: {
        count: 0,
        spec_id: 0,
      },
      role: 'hdfs_datanode',
      specClusterType: ClusterTypes.HDFS,
      specMachineType: 'hdfs_datanode',
      tagText: t('存储层'),
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);

  // 获取主机详情
  const fetchHostDetail = () => {
    isLoading.value = true;
    getHdfsMachineList({
      cluster_ids: String(props.clusterData.id),
      limit: -1,
      offset: 0,
    })
      .then((data) => {
        const datanodeOriginalHostList: HdfsMachineModel[] = [];

        let datanodeDiskTotal = 0;

        data.results.forEach((hostItem) => {
          if (hostItem.isDataNode) {
            datanodeDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            datanodeOriginalHostList.push(hostItem);
          }
        });

        nodeInfoMap.datanode.totalDisk = datanodeDiskTotal;
        nodeInfoMap.datanode.originalHostList = datanodeOriginalHostList;
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
