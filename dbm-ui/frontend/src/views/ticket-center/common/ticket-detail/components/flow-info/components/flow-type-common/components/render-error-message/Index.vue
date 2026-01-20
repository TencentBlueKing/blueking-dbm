<template>
  <FlowCollapse
    danger
    :title="t('失败原因')">
    <BkRadioGroup
      v-model="errorType"
      class="ml-16 mb-5"
      type="capsule">
      <BkRadioButton
        v-if="ENABLE_DBM_AI"
        label="ai">
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
        color: '#4D4F56',
        lineHeight: '20px',
        fontSize: '12px',
      }">
      <component
        :is="renderContent"
        :data="data"
        :ticket-detail="ticketDetail" />
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
  defineProps<Props>();
  const { t } = useI18n();

  const { ENABLE_DBM_AI } = useSystemEnviron().urls;

  const errorType = ref<'ai' | 'original'>('ai');

  const errMessageMaxHeight = window.innerHeight * 0.4;

  const renderContent = computed(() => {
    if (errorType.value === 'ai') {
      return LogAnnlysis;
    }
    return LogOriginal;
  });
</script>
