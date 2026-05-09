<template>
  <DbFormItem class="monitor-strategy-voice-notice">
    <div class="voice-notice">
      <span class="voice-notice-title mr-8">{{ t('语音拨打顺序') }}</span>
      <BkRadioGroup
        v-model="modelValue"
        @change="handleDataChange">
        <BkRadio label="serial">
          {{ t('串行') }}
        </BkRadio>
        <BkRadio label="parallel">
          {{ t('并行') }}
        </BkRadio>
      </BkRadioGroup>
      <BkPopover>
        <DbIcon
          class="voice-notice-icon ml-8"
          type="attention" />
        <template #content>
          <div>{{ t('并行：组间同时拨打，组内顺序依次拨打；') }}</div>
          <div>{{ t('串行：多个用户组人员顺序合并后依次拨打；') }}</div>
          <div>{{ t('重复人员以前置组优先') }}</div>
        </template>
      </BkPopover>
    </div>
  </DbFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    required: true,
  });

  type Emits = (e: 'change') => void;

  const { t } = useI18n();

  const handleDataChange = () => {
    emits('change');
  };
</script>

<style lang="less">
  .monitor-strategy-voice-notice {
    .voice-notice {
      display: flex;
      align-items: center;
      font-size: 12px;

      .voice-notice-title {
        color: #979ba5;
      }

      .voice-notice-icon {
        font-size: 14px;
      }

      .bk-radio ~ .bk-radio {
        margin-left: 12px;
      }
    }
  }
</style>
