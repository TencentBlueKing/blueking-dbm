<template>
  <DbFormItem
    :label="t('规格')"
    property="spec.spec_id"
    required>
    <SpecSelector
      ref="specSelectorRef"
      v-model="targetInfo.spec.spec_id"
      :biz-id="cluster.bk_biz_id"
      :cloud-id="cluster.bk_cloud_id"
      cluster-type="redis"
      :machine-type="specClusterMachineMap[cluster.cluster_type]"
      style="width: 314px"
      @update:model-value="handleChangeSpec" />
  </DbFormItem>
  <DbFormItem
    :label="t('数量')"
    property="groupNum"
    required
    :rules="rules">
    <BkInput
      v-model="groupNum"
      clearable
      :min="minGroupNum"
      show-clear-only-hover
      style="width: 314px"
      type="number"
      @change="handleChangeGroupNum" />
    <span class="input-desc">{{ t('组') }}</span>
  </DbFormItem>
  <DbFormItem
    :label="t('单机分片数')"
    property="shardNum"
    required>
    <BkInput
      v-model="targetInfo.shardNum"
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
      v-model="targetInfo.capacity"
      disabled
      :placeholder="t('自动生成')"
      style="width: 314px"
      type="number" />
    <span class="input-desc">G</span>
  </DbFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type RedisModel from '@services/model/redis/redis';

  import { ClusterTypes } from '@common/const';

  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';

  import { type TargetInfo } from '../Index.vue';

  interface Props {
    cluster: RedisModel;
  }
  type Emits = (e: 'change', data: typeof targetInfo.value) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const targetInfo = defineModel<TargetInfo>({ required: true });

  const { t } = useI18n();

  const specSelectorRef = ref<ComponentExposed<typeof SpecSelector>>();
  const groupNum = ref('');

  const shardNumDisabled = computed(() => props.cluster.cluster_type !== ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER);
  const clusterShardNum = computed(() => props.cluster.cluster_shard_num);
  const minGroupNum = computed(() => {
    // RedisCluster/ tendisplus 机器组数需要最少3组。
    if (
      [ClusterTypes.PREDIXY_REDIS_CLUSTER, ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER].includes(props.cluster.cluster_type)
    ) {
      return 3;
    }
    return 1;
  });

  const rules = [
    {
      message: t('组数不能为空'),
      trigger: 'change',
      validator: () => !!groupNum.value,
    },
    {
      message: t('必须要能除尽总分片数'),
      trigger: 'change',
      validator: (value: number) => {
        if (shardNumDisabled.value) {
          targetInfo.value.shardNum = Number((clusterShardNum.value / value).toFixed(2));
          return clusterShardNum.value % value === 0;
        }
        return true;
      },
    },
  ];

  const fetchUpdateInfo = () => {
    setTimeout(() => {
      // 单机分片数是否为整数
      if (targetInfo.value.shardNum % 1 !== 0) {
        return;
      }
      const data = specSelectorRef.value!.getData();
      if (_.isEmpty(data)) {
        return;
      }
      targetInfo.value.spec = data;
      targetInfo.value.capacity = Math.floor(targetInfo.value.groupNum * data.capacity);
      emits('change', targetInfo.value);
    });
  };

  const handleChangeSpec = (value: number | string) => {
    if (!value) {
      return;
    }
    fetchUpdateInfo();
  };

  const handleChangeGroupNum = (value: string) => {
    if (!value) {
      return;
    }
    targetInfo.value.groupNum = Number(value);
    fetchUpdateInfo();
  };

  onMounted(() => {
    if (props.cluster.id) {
      Object.assign(targetInfo.value, {
        capacity: props.cluster.cluster_capacity,
        clusterStats: props.cluster.cluster_stats,
        groupNum: props.cluster.machine_pair_cnt,
        shardNum: props.cluster.cluster_shard_num,
        spec: props.cluster.cluster_spec,
      });
    }
  });
</script>

<style lang="less" scoped>
  .input-desc {
    padding-left: 12px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
  }
</style>
