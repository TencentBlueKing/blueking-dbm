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
    <div class="tag-list">
      <div class="db-tag">{{ dbIdNameMap[data.db_type] || '--' }}</div>
      <TagBlock
        v-if="!isSpecial"
        class="inpact-list"
        :data="bizInpactList"
        size="small" />
    </div>

    <div
      v-overflow-tips
      class="desc">
      {{ data.description }}
    </div>
    <div class="time-display">
      <span
        v-if="!isSpecial"
        class="mr-6">
        {{ t('持续时间') }}：{{ durationTimeDisplay }}
      </span>
      <span>{{ t('最近更新') }}：{{ latestUpdateDisplay }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import TagBlock from '@components/tag-block/Index.vue';

  import { getCostTimeDisplay, utcDisplayTime } from '@utils';

  import { useIntervalFn } from '@vueuse/core';

  import { type RiskMemoItem } from '../Index.vue';

  interface Props {
    data: RiskMemoItem;
    dbIdNameMap?: Record<string, string>;
    effectBizLabelMap?: Record<string, string>;
    isActive?: boolean;
    isSpecial?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbIdNameMap: () => ({}),
    effectBizLabelMap: () => ({}),
    isActive: false,
    isSpecial: false,
  });

  const { t } = useI18n();

  const durationTimeDisplay = ref(getCostTimeDisplay(0));

  const isFinished = computed(() => props.data.status === 'done');
  const bizInpactList = computed(() => props.data.biz_inpact.map((item) => props.effectBizLabelMap[item] || ''));

  const latestUpdateDisplay = computed(() => {
    if (props.data.final_time) {
      return utcDisplayTime(props.data.final_time);
    }

    if (props.data.followup_update_at) {
      return utcDisplayTime(props.data.followup_update_at);
    }

    return utcDisplayTime(props.data.create_at);
  });

  // 计时
  const { pause, resume } = useIntervalFn(() => {
    const duratiopn = Math.floor(Date.now() / 1000) - dayjs(props.data.create_at).valueOf() / 1000;
    durationTimeDisplay.value = getCostTimeDisplay(duratiopn);
  }, 1000);

  watch(
    () => [props.data.status, props.isSpecial],
    () => {
      if (props.isSpecial) {
        pause();
        return;
      }

      if (props.data.status === 'done') {
        pause();
        const duration = dayjs(props.data.final_time).valueOf() / 1000 - dayjs(props.data.create_at).valueOf() / 1000;
        durationTimeDisplay.value = getCostTimeDisplay(duration);
      } else {
        // 进行中的动态更新
        resume();
      }
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    pause();
  });
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
      display: flex;
      align-items: center;

      .db-tag {
        height: 16px;
        background: #c4c6cc;
        border-radius: 2px;
        font-size: 10px;
        color: #ffffff;
        display: flex;
        align-items: center;
        padding: 0 4px;
        margin-right: 4px;
      }

      .inpact-list {
        flex: 1;
        overflow: hidden;
      }
    }

    .desc {
      flex: 1;
      display: -webkit-box;
      display: -moz-box;
      display: box;
      -webkit-box-orient: vertical;
      -moz-box-orient: vertical;
      box-orient: vertical;
      -webkit-line-clamp: 6;
      -moz-line-clamp: 6;
      line-clamp: 6;
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
