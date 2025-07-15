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
    :title="t('xx扩容【name】', { title: 'Kafka', name: clusterData.cluster_name })"
    @submit="handleChange" />
</template>
<script setup lang="tsx">
  import { reactive, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type KafkaModel from '@services/model/kafka/kafka';
  import kafkaMachineModel from '@services/model/kafka/kafka-machine';
  import { getKafkaMachineList } from '@services/source/kafka';

  import { ClusterTypes } from '@common/const';

  import MachineExpansion, { type TExpansionNode } from '@views/db-manage/common/machine-expansion/Index.vue';

  interface Props {
    clusterData: KafkaModel;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<string, TExpansionNode>>({
    broker: {
      clusterId: props.clusterData.id,
      // targetDisk: 0,
      expansionDisk: 0,
      hostList: [],
      ipSource: 'resource_pool',
      label: 'Broker',
      originalHostList: [],
      resourceSpec: {
        count: 0,
        spec_id: 0,
      },
      role: 'broker',
      specClusterType: ClusterTypes.KAFKA,
      specMachineType: 'broker',
      tagText: t('存储层'),
      totalDisk: 0,
    },
  });

  const isLoading = ref(false);

  // 获取主机详情
  const fetchHostDetail = () => {
    isLoading.value = true;
    getKafkaMachineList({
      cluster_ids: String(props.clusterData.id),
      limit: -1,
      offset: 0,
    })
      .then((data) => {
        const brokerOriginalHostList: kafkaMachineModel[] = [];

        let brokerDiskTotal = 0;

        data.results.forEach((hostItem) => {
          if (hostItem.isBroker) {
            brokerDiskTotal += Math.floor(Number(hostItem.host_info.bk_disk));
            brokerOriginalHostList.push(hostItem);
          }
        });

        nodeInfoMap.broker.totalDisk = brokerDiskTotal;
        nodeInfoMap.broker.originalHostList = brokerOriginalHostList;
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
