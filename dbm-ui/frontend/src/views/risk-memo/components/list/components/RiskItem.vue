<template>
  <div
    class="risk-info-item"
    :class="{ 'is-finished': isFinished, 'is-active': isActive }">
    <div class="title-main">
      <div
        v-overflow-tips
        class="title">
        {{ data.name }}
      </div>
      <BkTag
        v-if="isFinished"
        size="small">
        {{ isSpecial ? t('已失效') : t('已结项') }}
      </BkTag>
      <BkTag
        v-else
        size="small"
        theme="success">
        {{ t('进行中') }}
      </BkTag>
    </div>
    <TagBlock
      v-if="!isSpecial"
      class="tag-list"
      :data="bizInpactList"
      size="small" />
    <div
      v-overflow-tips
      class="desc">
      {{ data.description }}
    </div>
    <div
      v-if="!isSpecial"
      class="time-display">
      {{ t('持续时间') }}：{{ getCostTimeDisplay(data.duration_time) }}
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TagBlock from '@components/tag-block/Index.vue';

  import { getCostTimeDisplay } from '@utils';

  import { type RiskMemoItem } from '../Index.vue';

  interface Props {
    data: RiskMemoItem;
    effectBizLabelMap?: Record<string, string>;
    isActive?: boolean;
    isSpecial?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    effectBizLabelMap: () => ({}),
    isActive: false,
    isSpecial: false,
  });

  const { t } = useI18n();

  const isFinished = computed(() => props.data.status === 'done');
  const bizInpactList = computed(() => props.data.biz_inpact.map((item) => props.effectBizLabelMap[item] || ''));
</script>
<style lang="less">
  .risk-info-item {
    width: 100%;
    padding: 12px 12px 8px 12px;
    display: flex;
    flex-direction: column;
    cursor: pointer;
    border-radius: 2px;
    border-bottom: 1px solid #eaebf0;

    &:hover {
      background-color: #f0f1f5;
    }

    &.is-finished {
      color: #c4c6cc;

      .bk-tag-text,
      .time-display {
        color: #c4c6cc;
      }
    }

    &.is-active {
      background-color: #e1ecff;
    }

    .title-main {
      width: 100%;
      display: flex;
      align-items: center;
      margin-bottom: 8px;

      .title {
        font-weight: 700;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .tag-list {
      width: 100%;
      margin-bottom: 4px;
    }

    .desc {
      flex: 1;
      display: -webkit-box;
      display: -moz-box;
      display: box;
      -webkit-box-orient: vertical;
      -moz-box-orient: vertical;
      box-orient: vertical;
      -webkit-line-clamp: 2;
      -moz-line-clamp: 2;
      line-clamp: 2;
      overflow: hidden;
      text-overflow: ellipsis;
      line-height: 20px;
    }

    .time-display {
      font-size: 12px;
      margin-top: 8px;
      font-family: ArialMT;
      color: #979ba5;
    }
  }
</style>
