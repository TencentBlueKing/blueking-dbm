<template>
  <div class="redis-detail-shard-capacity-cell">
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

  import type { DetailSpecs } from '@services/model/ticket/details/common';

  import RenderSpec from '@components/spec-display/Index.vue';

  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';

  interface Props {
    diffData?: Props['displayData'];
    displayData: {
      capacity: number;
      clusterShardNum: number;
      groupNum: number;
      machineShardNum: number;
      spec: DetailSpecs[string];
    };
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less">
  .redis-detail-shard-capacity-cell {
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
