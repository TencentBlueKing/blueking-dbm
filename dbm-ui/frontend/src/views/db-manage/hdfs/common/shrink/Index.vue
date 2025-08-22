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
    :title="t('xx缩容【name】', { title: 'HDFS', name: clusterData?.cluster_name })"
    @submit="handleChange" />
</template>
<script setup lang="tsx">
  import { reactive, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import HdfsModel from '@services/model/hdfs/hdfs';
  import HdfsMachineModel from '@services/model/hdfs/hdfs-machine';
  import { getHdfsNodeList } from '@services/source/hdfs';

  import MachineShrink, { type TShrinkNode } from '@views/db-manage/common/machine-shrink/Index.vue';

  interface Props {
    clusterData: HdfsModel;
    machineList?: HdfsMachineModel[];
  }

  const props = withDefaults(defineProps<Props>(), {
    machineList: () => [],
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  type Emits = (e: 'change') => void;

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<'datanode', TShrinkNode>>({
    datanode: {
      hostList: [],
      label: 'DataNode',
      // 最小主机数
      minHost: 2,
      originalNodeList: [],
      // 缩容后的目标容量
      // targetDisk: 0,
      // 实际选择的缩容主机容量
      shrinkDisk: 0,
      tagText: t('存储层'),
      // 当前主机总容量
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);

  const fetchListNode = () => {
    const datanodeOriginalNodeList: TShrinkNode['originalNodeList'] = [];

    isLoading.value = true;
    getHdfsNodeList({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.clusterData.id,
      no_limit: 1,
    })
      .then((data) => {
        let datanodeDiskTotal = 0;

        data.results.forEach((nodeItem) => {
          if (nodeItem.isDataNode) {
            datanodeDiskTotal += nodeItem.disk;
            datanodeOriginalNodeList.push(nodeItem);
          }
        });

        nodeInfoMap.datanode.originalNodeList = datanodeOriginalNodeList;
        nodeInfoMap.datanode.totalDisk = datanodeDiskTotal;
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
      const datanodeList: TShrinkNode['hostList'] = [];

      let datanodeShrinkDisk = 0;

      props.machineList.forEach((machineItem) => {
        if (machineItem.isDataNode) {
          datanodeShrinkDisk += machineItem.host_info?.bk_disk || 0;
          datanodeList.push({
            alive: machineItem.host_info?.alive || 0,
            bk_cloud_id: machineItem.bk_cloud_id,
            bk_disk: machineItem.host_info.bk_disk,
            bk_host_id: machineItem.bk_host_id,
            ip: machineItem.ip,
          });
        }
      });
      nodeInfoMap.datanode.hostList = datanodeList;
      nodeInfoMap.datanode.shrinkDisk = datanodeShrinkDisk;
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    emits('change');
  };
</script>
