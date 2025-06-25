<template>
  <div class="redis-capacity-cell">
    <div class="display-content">
      <div class="item">
        <div class="item-title">{{ t('容量') }}：</div>
        <div class="item-content">
          <span class="number-style">{{ data.capacity }}</span>
          G
          <ValueDiff
            v-if="originData?.capacity"
            :current-value="originData.capacity"
            num-unit="G"
            :target-value="data.capacity" />
        </div>
      </div>
      <div class="item">
        <div class="item-title">{{ t('资源规格') }}：</div>
        <div class="item-content">
          <RenderSpec
            :data="data.spec"
            :hide-qps="!data.spec?.qps?.max"
            is-ignore-counts />
        </div>
      </div>
      <div class="item">
        <div class="item-title">{{ t('机器组数') }}：</div>
        <div class="item-content">
          <span class="number-style">{{ data.groupNum }}</span>
          <ValueDiff
            v-if="originData?.groupNum"
            :current-value="originData.groupNum"
            :show-rate="false"
            :target-value="data.groupNum" />
        </div>
      </div>
      <div class="item">
        <div class="item-title">{{ t('机器数量') }}：</div>
        <div class="item-content">
          <span class="number-style">{{ data.groupNum * 2 }}</span>
          <ValueDiff
            v-if="originData?.groupNum"
            :current-value="originData.groupNum * 2"
            :show-rate="false"
            :target-value="data.groupNum * 2" />
        </div>
      </div>
      <div class="item">
        <div class="item-title">{{ t('集群分片数') }}：</div>
        <div class="item-content">
          <span class="number-style">{{ data.clusterShardNum }}</span>
          <ValueDiff
            v-if="originData?.clusterShardNum"
            :current-value="originData.clusterShardNum"
            :show-rate="false"
            :target-value="data.clusterShardNum" />
        </div>
      </div>
      <slot />
    </div>
  </div>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import ValueDiff from '@views/db-manage/common/value-diff/Index.vue';

  import RenderSpec from './render-spec/Index.vue';

  interface Props {
    data: {
      capacity: number;
      clusterShardNum: number;
      groupNum: number;
      spec: any;
    };
    originData?: Props['data'];
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less">
  .redis-capacity-cell {
    width: 100%;
    overflow: hidden;

    :deep(.render-spec-box) {
      height: 22px !important;
      padding: 0 !important;
    }

    .display-content {
      padding: 11px 16px;
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
