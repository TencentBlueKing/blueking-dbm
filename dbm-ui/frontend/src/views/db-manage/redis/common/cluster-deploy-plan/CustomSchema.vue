<template>
  <div class="custom-schema">
    <DbFormItem
      :label="t('规格')"
      property="specId"
      required>
      <SpecSelector
        ref="specSelectorRef"
        v-model="modelValue.specId"
        :biz-id="clusterInfo.bizId"
        :cloud-id="clusterInfo.cloudId"
        cluster-type="redis"
        :machine-type="specClusterMachineMap[clusterInfo.clusterType]"
        style="width: 314px" />
    </DbFormItem>
    <DbFormItem
      :label="t('数量')"
      property="count"
      required
      :rules="countRules">
      <BkInput
        v-model="modelValue.count"
        clearable
        :min="1"
        show-clear-only-hover
        style="width: 314px"
        type="number" />
      <span class="input-desc">{{ t('组') }}</span>
    </DbFormItem>
    <DbFormItem
      :label="t('单机分片数')"
      property="shardNum"
      required
      :rules="shardNumRules">
      <BkInput
        v-model="modelValue.shardNum"
        clearable
        :disabled="shardNumDisabled"
        :min="1"
        show-clear-only-hover
        style="width: 314px"
        type="number" />
    </DbFormItem>
    <DbFormItem
      :label="t('集群分片数')"
      :required="false">
      <BkInput
        v-model="modelValue.clusterShardNum"
        disabled
        :placeholder="t('自动生成')"
        style="width: 314px"
        type="number" />
    </DbFormItem>
    <DbFormItem
      :label="t('总容量')"
      :required="false">
      <BkInput
        v-model="modelValue.totalCapcity"
        disabled
        :placeholder="t('自动生成')"
        style="width: 314px"
        type="number" />
      <span class="input-desc">G</span>
    </DbFormItem>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';

  import { specClusterMachineMap } from '../const';

  interface Props {
    clusterInfo: {
      bizId: number | string;
      cloudId: number | string;
      clusterType: string;
      machineType: string;
    };
    shardNumDisabled?: boolean;
  }

  interface ModelValue {
    clusterShardNum: number;
    count: number;
    shardNum: number;
    specId: number | string;
    totalCapcity: number;
  }

  interface Expose {
    getInfo(): {
      cluster_capacity: number;
      cluster_shard_num: number;
      machine_pair: number;
    } & ReturnType<ComponentExposed<typeof SpecSelector>['getData']>;
  }

  const props = withDefaults(defineProps<Props>(), {
    shardNumDisabled: false,
  });
  const modelValue = defineModel<ModelValue>({ required: true });

  const { t } = useI18n();

  const specSelectorRef = ref<ComponentExposed<typeof SpecSelector>>();

  const countRules = [
    {
      message: t('必须要能除尽总分片数'),
      trigger: 'change',
      validator: (value: number) => {
        if (props.shardNumDisabled) {
          return modelValue.value.clusterShardNum % value === 0;
        }
        return true;
      },
    },
  ];

  const shardNumRules = [
    {
      message: t('请输入单机分片数'),
      trigger: 'change',
      validator: (value: number) => value > 0,
    },
  ];

  watch(
    () => [modelValue.value.count, modelValue.value.shardNum],
    ([newCount, newShardNum]) => {
      if (!props.shardNumDisabled) {
        modelValue.value.clusterShardNum = newCount * newShardNum;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => modelValue.value.count,
    () => {
      if (props.shardNumDisabled) {
        if (modelValue.value.count) {
          modelValue.value.shardNum = Number((modelValue.value.clusterShardNum / modelValue.value.count).toFixed(2));
        } else {
          modelValue.value.shardNum = 0;
        }
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [modelValue.value.specId, modelValue.value.count],
    () => {
      nextTick(() => {
        const data = specSelectorRef.value!.getData();

        if (_.isEmpty(data)) {
          return '';
        }

        modelValue.value.totalCapcity = modelValue.value.count * getSpecCapacity(data);
      });
    },
    {
      immediate: true,
    },
  );

  const getSpecCapacity = (resourceSpec: ReturnType<ComponentExposed<typeof SpecSelector>['getData']>) => {
    if (
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER, ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE].includes(
        props.clusterInfo.clusterType as ClusterTypes,
      )
    ) {
      const specItem = resourceSpec.storage_spec.find((storageSpecItem) => storageSpecItem.mount_point === '/data1');
      return specItem?.size || 0;
    }
    return resourceSpec.mem.min;
  };

  defineExpose<Expose>({
    getInfo() {
      const specData = specSelectorRef.value!.getData();
      return {
        cluster_capacity: modelValue.value.totalCapcity || 0,
        cluster_shard_num: modelValue.value.shardNum,
        cpu: specData.cpu,
        machine_pair: modelValue.value.count,
        mem: specData.mem,
        qps: specData.qps,
        spec_name: specData?.spec_name || '',
        storage_spec: specData.storage_spec,
      };
    },
  });
</script>

<style lang="less" scoped>
  .custom-schema {
    // max-width: 1200px;
    // padding: 24px 24px 24px 10px;
    // background-color: #f5f7fa;
    // border-radius: 2px;

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }
  }
</style>
