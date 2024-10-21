<template>
  <div class="custom-schema">
    <DbFormItem
      :label="t('规格')"
      property="details.resource_spec.backend_group.spec_id"
      required>
      <SpecSelector
        ref="specSelectorRef"
        v-model="modelValue.spec_id"
        :biz-id="bizId"
        :cloud-id="cloudId"
        :cluster-type="clusterType"
        :machine-type="machineType"
        style="width: 314px" />
    </DbFormItem>
    <DbFormItem
      :label="t('数量')"
      property="details.resource_spec.backend_group.count"
      required>
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
      required>
      <BkInput
        v-model="shardNum"
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
        v-model="clusterShardNum"
        disabled
        :placeholder="t('自动生成')"
        style="width: 314px"
        type="number" />
    </DbFormItem>
    <DbFormItem
      :label="t('总容量')"
      :required="false">
      <BkInput
        v-model="totalCapcity"
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
    clusterType: string;
    machineType: string;
    bizId: number | string;
    cloudId: number | string;
    shardNumDisabled?: boolean;
  }

  interface ModelValue {
    spec_id: number | string;
    count: number;
  }

  interface Expose {
    getInfo(): {
      spec_name: string;
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
  const shardNum = ref(1);

  const clusterShardNum = computed(() => modelValue.value.count * shardNum.value || '');

  const totalCapcity = computed(() => {
    const data = specSelectorRef.value?.getData();
    const { count } = modelValue.value;

    if (_.isEmpty(data)) {
      return '';
    }

    return count * getSpecCapacity(data) || '';
  });

  const getSpecCapacity = (resourceSpec: ReturnType<ComponentExposed<typeof SpecSelector>['getData']>) => {
    if (
      [ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER, ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE].includes(
        props.clusterType as ClusterTypes,
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
        cluster_shard_num: shardNum.value,
        cluster_capacity: totalCapcity.value || 0,
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
