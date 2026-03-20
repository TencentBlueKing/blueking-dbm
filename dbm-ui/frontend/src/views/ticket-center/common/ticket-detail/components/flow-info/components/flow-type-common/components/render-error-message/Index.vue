<template>
  <FlowCollapse
    v-if="isShow"
    danger
    :title="t('失败原因')">
    <!-- ENABLE_DBM_AI 为 true 时，才显示 AI 日志分析和原始日志选择 -->
    <!-- 两个都存在时才显示 tab 切换，所以 ENABLE_DBM_AI 为 false 时，不显示 BkRadioGroup -->
    <BkRadioGroup
      v-if="isShowAiLog"
      v-model="errorType"
      class="ml-16 mb-5"
      type="capsule">
      <BkRadioButton label="ai">
        <img
          :src="AiBluekingImage"
          style="width: 12px" />
        {{ t('AI 日志分析') }}
      </BkRadioButton>
      <BkRadioButton label="original">
        <DbIcon type="file" />
        {{ t('原始日志') }}
      </BkRadioButton>
    </BkRadioGroup>
    <div
      class="pl-16"
      :style="{
        'max-height': `${errMessageMaxHeight}px`,
        overflow: 'auto',
        height: logContentHeight,
        color: '#4D4F56',
        lineHeight: '20px',
        fontSize: '12px',
      }">
      <component
        :is="renderContent"
        :data="data"
        :ticket-detail="ticketDetail"
        @element-height-change="handleElementHeightChange" />
    </div>
  </FlowCollapse>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { useSystemEnviron } from '@stores';

  import AiBluekingImage from '@images/ai-blueking.svg';

  import FlowCollapse from '../../components/FlowCollapse.vue';

  import LogAnnlysis from './components/log-annlysis.vue';
  import LogOriginal from './components/log-original.vue';

  interface Props {
    data: FlowMode<unknown, any>;
    ticketDetail: TicketModel<unknown>;
  }
  const props = defineProps<Props>();
  const { t } = useI18n();
  const errMessageMaxHeight = window.innerHeight * 0.4;

  const { ENABLE_DBM_AI } = useSystemEnviron().urls;

  const isShowAiLog = ENABLE_DBM_AI && props.data.err_code !== 4;
  const errorType = ref<'ai' | 'original'>(isShowAiLog ? 'ai' : 'original');
  const logContentHeight = ref('auto');

  const isShow = computed(() => {
    return [
      FlowMode.TYPE_HOST_RECYCLE,
      FlowMode.TYPE_INNER_FLOW,
      FlowMode.TYPE_INNER_FLOW,
      FlowMode.TYPE_RESOURCE_APPLY,
      FlowMode.TYPE_RESOURCE_HCM_REPLENISH,
    ].includes(props.data.flow_type);
  });

  const renderContent = computed(() => {
    if (errorType.value === 'ai') {
      return LogAnnlysis;
    }
    return LogOriginal;
  });

  const handleElementHeightChange = (height: number) => {
    if (height >= errMessageMaxHeight) {
      logContentHeight.value = `${height}px`;
    }
  };
</script>
