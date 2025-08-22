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
    :title="t('xx替换【name】', { title: 'Kafka', name: clusterData?.cluster_name })"
    @remove-node="handleRemoveNode"
    @submit="handleChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import KafkaModel from '@services/model/kafka/kafka';
  import KafkaMachineModel from '@services/model/kafka/kafka-machine';

  import { ClusterTypes } from '@common/const';

  import MachineReplace, { type TReplaceNode } from '@views/db-manage/common/machine-replace/Index.vue';

  interface Props {
    clusterData: KafkaModel;
    machineList?: KafkaMachineModel[];
  }

  interface Emits {
    (e: 'change'): void;
    (e: 'removeNode', bkHostId: number): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    machineList: () => [],
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const nodeInfoMap = reactive<Record<'broker' | 'zookeeper', TReplaceNode>>({
    broker: {
      clusterId: props.clusterData.id,
      hostList: [],
      label: 'Broker',
      oldHostList: [],
      resourceSpec: {
        count: 3,
        spec_id: 0,
      },
      role: 'broker',
      specClusterType: ClusterTypes.KAFKA,
      specMachineType: 'broker',
    },
    zookeeper: {
      clusterId: props.clusterData.id,
      hostList: [],
      label: 'Zookeeper',
      oldHostList: [],
      resourceSpec: {
        count: 0,
        spec_id: 0,
      },
      role: 'zookeeper',
      specClusterType: ClusterTypes.KAFKA,
      specMachineType: 'zookeeper',
    },
  });

  watch(
    () => props.machineList,
    () => {
      const brokerList: TReplaceNode['oldHostList'] = [];
      const zookeeperList: TReplaceNode['oldHostList'] = [];

      props.machineList.forEach((machineItem) => {
        if (machineItem.isBroker) {
          brokerList.push(machineItem);
        } else if (machineItem.isZookeeper) {
          zookeeperList.push(machineItem);
        }
      });

      nodeInfoMap.broker.oldHostList = brokerList;
      nodeInfoMap.zookeeper.oldHostList = zookeeperList;
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
