<template>
  <div class="redis-shard-capacity-cell">
    <div class="display-content">
      <div class="item">
        <div class="item-title">{{ t('容量') }}：</div>
        <div class="item-content">
          <span class="number-style">{{ displayData.capacity }}</span>
          G
          <ValueDiff
            v-if="diffData?.capacity"
            :current-value="diffData.capacity"
            num-unit="G"
            :target-value="displayData.capacity" />
        </div>
      </div>
      <div class="item">
        <div class="item-title">{{ t('资源规格') }}：</div>
        <div class="item-content">
          <RenderSpec
            :data="displayData.spec"
            is-ignore-counts />
        </div>
      </div>
      <div class="item">
        <div class="item-title">{{ t('机器组数') }}：</div>
        <div class="item-content">
          <span class="number-style">{{ displayData.groupNum }}</span>
          <ValueDiff
            v-if="diffData?.groupNum"
            :current-value="diffData.groupNum"
            :show-rate="false"
            :target-value="displayData.groupNum" />
        </div>
      </div>
      <div class="item">
        <div class="item-title">{{ t('集群分片数') }}：</div>
        <div class="item-content">
          <span class="number-style">{{ displayData.clusterShardNum }}</span>
          <ValueDiff
            v-if="diffData?.clusterShardNum"
            :current-value="diffData.clusterShardNum"
            :show-rate="false"
            :target-value="displayData.clusterShardNum" />
        </div>
      </div>
      <div class="item">
        <div class="item-title">{{ t('单机分片数') }}：</div>
        <div class="item-content">
          <span class="number-style">{{ displayData.machineShardNum }}</span>
          <ValueDiff
            v-if="diffData?.machineShardNum"
            :current-value="diffData.machineShardNum"
            :show-rate="false"
            :target-value="displayData.machineShardNum" />
        </div>
      </div>
      <slot />
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RedisModel from '@services/model/redis/redis';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { ClusterTypes } from '@common/const';

  import RenderSpec from '@components/spec-display/Index.vue';

  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';

  interface Props {
    cluster: {
      cluster_capacity: number;
      cluster_shard_num: number;
      cluster_spec: RedisModel['cluster_spec'];
      id: number;
      machine_pair_cnt: number;
    };
    diffGroupNum?: number;
    type: 'current' | 'target';
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const displayData = computed(() => {
    const data = formatClusterData();

    if (props.type === 'current') {
      return data;
    }

    const groupNum = props.cluster.machine_pair_cnt + props.diffGroupNum!;
    return {
      capacity: getTargetCapacity(groupNum),
      clusterShardNum: groupNum * data.machineShardNum,
      groupNum: groupNum,
      machineShardNum: data.machineShardNum,
      spec: data.spec,
    };
  });

  const diffData = computed(() => {
    if (props.type === 'current') {
      return;
    }

    return formatClusterData();
  });

  const { data: specData, run: runGetResourceSpecList } = useRequest(getResourceSpecList, {
    manual: true,
  });

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id && props.type === 'target') {
        runGetResourceSpecList({
          enable: true,
          limit: -1,
          spec_cluster_type: ClusterTypes.REDIS,
          spec_ids: `${props.cluster.cluster_spec.spec_id}`,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const formatClusterData = () => ({
    capacity: props.cluster.cluster_capacity,
    clusterShardNum: props.cluster.cluster_shard_num,
    groupNum: props.cluster.machine_pair_cnt,
    machineShardNum: props.cluster.cluster_shard_num / props.cluster.machine_pair_cnt,
    spec: {
      ...props.cluster.cluster_spec,
      name: props.cluster.cluster_spec.spec_name,
    },
  });

  const getTargetCapacity = (groupNum: number) => {
    if (specData && specData.value && specData.value.results.length > 0) {
      const capacity = Math.floor(groupNum * specData.value.results[0].capacity);
      modelValue.value = capacity;
      return capacity;
    } else {
      modelValue.value = 0;
      return 0;
    }
  };
</script>

<style lang="less">
  .redis-shard-capacity-cell {
    width: 100%;
    overflow: hidden;

    .render-spec-box {
      height: 22px !important;
      padding: 0 !important;
    }

    .display-content {
      line-height: 20px;
      white-space: nowrap;

      .item {
        display: flex;
        width: 100%;

        .item-title {
          width: 70px;
          text-align: right;
        }

        .item-content {
          flex: 1;
          display: flex;
          align-items: center;

          .percent {
            margin-left: 4px;
            font-size: 12px;
            font-weight: bold;
            color: #313238;
          }

          .spec {
            margin-left: 2px;
            font-size: 12px;
            color: #979ba5;
          }
        }
      }
    }

    .number-style {
      margin: 0 2px;
      font-size: 12px;
      font-weight: 700;
      color: #313238;
    }
  }
</style>
