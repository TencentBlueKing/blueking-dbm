<template>
  <div class="replace-resource-pool-selector">
    <BkSelect
      :loading="isResourceSpecLoading"
      :model-value="modelValue.spec_id || undefined"
      @change="handleChange">
      <BkOption
        v-for="item in resourceSpecList?.results"
        :key="item.spec_id"
        :label="item.spec_name"
        :value="item.spec_id" />
    </BkSelect>
  </div>
</template>
<script setup lang="ts"
generic="T extends EsNodeModel|HdfsNodeModel|KafkaNodeModel|PulsarNodeModel|InfluxdbInstanceModel">
  import { useRequest } from 'vue-request';

  import { fetchRecommendSpec } from '@services/dbResource';
  import type EsNodeModel from '@services/model/es/es-node';
  import type HdfsNodeModel from '@services/model/hdfs/hdfs-node';
  import InfluxdbInstanceModel from '@services/model/influxdb/influxdbInstance';
  import type KafkaNodeModel from '@services/model/kafka/kafka-node';
  import type PulsarNodeModel from '@services/model/pulsar/pulsar-node';
  import { getResourceSpecList } from '@services/resourceSpec';

  import type { TReplaceNode } from '../Index.vue';

  interface Props {
    data: TReplaceNode<T>,
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<Props['data']['resourceSpec']>({
    required: true,
  });

  const {
    loading: isResourceSpecLoading,
    data: resourceSpecList,
  } = useRequest(getResourceSpecList, {
    defaultParams: [
      {
        spec_cluster_type: props.data.specClusterType,
        spec_machine_type: props.data.specMachineType,
      },
    ],
  });

  const getDefaultParams = ():{
    role: string,
    instance_id: number,
  }|{
    role: string,
    cluster_id: number,
  } => {
    // influxdb 没有 cluster_id 需要通过 instance_id 查询
    if (props.data.role === 'influxdb') {
      // eslint-disable-next-line vue/no-setup-props-destructure
      const [firstNode] = props.data.nodeList;
      if (firstNode instanceof InfluxdbInstanceModel) {
        return {
          role: props.data.role,
          instance_id: firstNode.id,
        };
      }
    }
    // 大数据集群同步 cluster_id 查询
    return {
      role: props.data.role,
      cluster_id: props.data.clusterId,
    };
  };

  useRequest(fetchRecommendSpec, {
    defaultParams: [getDefaultParams()],
    onSuccess(recommendSpecList) {
      if (recommendSpecList.length > 0) {
        modelValue.value.spec_id = recommendSpecList[0].spec_id;
      }
    },
  });

  const handleChange = (value: number) => {
    modelValue.value = {
      spec_id: value,
      count: props.data.nodeList.length,
    };
  };
</script>
<style lang="less" scoped>
  .replace-resource-pool-selector {
    position: absolute;
    inset: 43px 0 1px 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }
</style>
