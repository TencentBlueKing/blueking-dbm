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
        content: plainTextDescription,
        disabled: !isShowToolTip,
        extCls: 'risk-memo-desc-tooltips',
        placement: 'right',
        delay: 300,
      }"
      class="desc">
      {{ plainTextDescription }}
    </div>
    <div
      v-if="showBiz"
      class="info-display">
      {{ t('业务') }}：{{ bizIdMap.get(data.bk_biz_id)?.name || '--' }}
    </div>
    <div class="info-display">
      <span
        v-if="!isSpecial"
        class="mr-16">
        <span>{{ t('持续时间') }}：</span>
        <DurationDisplay
          :end-time="data.final_time"
          :start-time="data.create_at" />
      </span>
      <span>{{ t('最近更新') }}：{{ latestUpdateDisplay }}</span>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import TagBlock from '@components/tag-block/Index.vue';

  import { utcDisplayTime } from '@utils';

  import DurationDisplay from '../../DurationDisplay.vue';
  import { type RiskMemoItem } from '../Index.vue';

  interface Props {
    data: RiskMemoItem;
    dbIdNameMap?: Record<string, string>;
    effectBizLabelMap?: Record<string, string>;
    isActive?: boolean;
    isSpecial?: boolean;
    showBiz?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    dbIdNameMap: () => ({}),
    effectBizLabelMap: () => ({}),
    isActive: false,
    isSpecial: false,
    showBiz: false,
  });

  const { t } = useI18n();
  const { bizIdMap } = useGlobalBizs();

  const descRef = ref<HTMLElement>();
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

  // 去除 HTML 标签，提取纯文本
  const stripHtmlTags = (html: string): string => {
    if (!html || typeof html !== 'string') {
      return '';
    }

    // 创建一个临时 DOM 元素来解析 HTML
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = html;

    // 获取纯文本内容
    const text = tempDiv.textContent || tempDiv.innerText || '';

    // 清理多余的空白字符
    return text.trim().replace(/\s+/g, ' ');
  };

  // 纯文本描述
  const plainTextDescription = computed(() => stripHtmlTags(props.data.description || ''));

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
        font-size: 14px;
        font-weight: 700;
        color: #313238;
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

    .info-display {
      margin-top: 8px;
      font-family: ArialMT, Arial, sans-serif;
      color: #979ba5;
    }
  }

  .risk-memo-desc-tooltips {
    width: 600px;
    word-break: break-all;
  }
</style>
