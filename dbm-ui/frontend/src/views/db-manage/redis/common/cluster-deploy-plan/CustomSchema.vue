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
        :cluster-type="clusterInfo.clusterType"
        :machine-type="clusterInfo.machineType"
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
      required>
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

  interface Props {
    clusterInfo: {
      clusterType: string;
      machineType: string;
      bizId: number | string;
      cloudId: number | string;
    };
    shardNumDisabled?: boolean;
  }

  interface ModelValue {
    specId: number | string;
    count: number;
    shardNum: number;
    clusterShardNum: number;
    totalCapcity: number;
  }

  interface Expose {
    getInfo(): ReturnType<ComponentExposed<typeof SpecSelector>['getData']> & {
      machine_pair: number;
      cluster_shard_num: number;
      cluster_capacity: number;
    };
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
        spec_name: specData?.spec_name || '',
        machine_pair: modelValue.value.count,
        cluster_shard_num: modelValue.value.shardNum,
        cluster_capacity: modelValue.value.totalCapcity || 0,
        cpu: specData.cpu,
        mem: specData.mem,
        qps: specData.qps,
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
