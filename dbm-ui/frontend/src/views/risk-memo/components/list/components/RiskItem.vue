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
      ref="descRef"
      v-bk-tooltips="{
        content: data.description,
        disabled: !isShowToolTip,
        extCls: 'risk-memo-desc-tooltips',
      }"
      class="desc">
      {{ data.description }}
    </div>
    <div class="time-display">
      <span
        v-if="!isSpecial"
        class="mr-16">
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

  const descRef = ref<HTMLElement>();
  const durationTimeDisplay = ref(getCostTimeDisplay(0));
  const isShowToolTip = ref(false);

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

  onMounted(() => {
    const resizeObserver = new ResizeObserver(() => {
      const descScrollHeight = descRef.value!.scrollHeight;
      isShowToolTip.value = descScrollHeight > 120;
    });
    resizeObserver.observe(descRef.value!);

    onBeforeUnmount(() => {
      resizeObserver.unobserve(descRef.value!);
      resizeObserver.disconnect();
    });
  });

  onBeforeUnmount(() => {
    pause();
  });
</script>
<style lang="less">
  .risk-info-item {
    display: flex;
    width: 100%;
    padding: 12px 12px 8px;
    cursor: pointer;
    border-bottom: 1px solid #eaebf0;
    border-radius: 2px;
    flex-direction: column;

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
      display: flex;
      width: 100%;
      margin-bottom: 8px;
      align-items: center;

      .title {
        overflow: hidden;
        font-weight: 700;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
      }
    }

    .tag-list {
      display: flex;
      width: 100%;
      margin-bottom: 4px;
      align-items: center;

      .db-tag {
        display: flex;
        height: 16px;
        padding: 0 4px;
        font-size: 10px;
        color: #fff;
        background: #c4c6cc;
        border-radius: 2px;
        align-items: center;
      }

      .inpact-list {
        flex: 1;
        overflow: hidden;

        .bk-tag {
          margin-left: 4px;
        }
      }
    }

    .desc {
      display: -webkit-box;
      display: -moz-box;
      overflow: hidden;
      line-height: 20px;
      text-overflow: ellipsis;
      word-break: break-all;
      -webkit-box-orient: vertical;
      flex: 1;
      -webkit-line-clamp: 6;
      -moz-line-clamp: 6;
      line-clamp: 6;
    }

    .time-display {
      margin-top: 8px;
      font-family: ArialMT, Arial, sans-serif;
      font-size: 12px;
      color: #979ba5;
    }
  }

  .risk-memo-desc-tooltips {
    width: 600px;
    word-break: break-all;
  }
</style>
