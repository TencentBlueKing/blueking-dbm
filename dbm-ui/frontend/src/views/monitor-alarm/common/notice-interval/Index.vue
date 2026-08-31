<template>
  <div class="notice-interval">
    <div class="notice-interval-row">
      <BkSelect
        v-model="mode"
        behavior="simplicity"
        class="interval-select"
        :clearable="false"
        @change="handleChange">
        <BkOption
          key="standard"
          :label="t('固定')"
          value="standard" />
        <BkOption
          key="increasing"
          :label="t('递增')"
          value="increasing" />
      </BkSelect>
      <span class="interval-text">{{ t('间隔') }}</span>
      <BkInput
        v-model="interval"
        behavior="simplicity"
        class="interval-input"
        :min="1"
        type="number"
        @change="handleChange" />
      <span class="interval-text">{{ t('分钟再进行告警') }}</span>
      <BkPopover placement="top">
        <DbIcon type="attention" />
        <template #content>
          <div class="interval-desc">{{ intervalDesc }}</div>
          <div
            v-if="mode === 'increasing'"
            class="interval-desc interval-tip">
            {{ intervalIncreasingTip }}
          </div>
        </template>
      </BkPopover>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref, type UnwrapRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

  interface Props {
    data: Omit<MonitorPolicyModel['notify_config'], 'voice_notice'>;
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    getValue: () => Props['data'];
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const mode = ref<'standard' | 'increasing'>('standard');
  const interval = ref<number>(0);

  watch(
    () => props.data,
    () => {
      mode.value = props.data.interval_notify_mode as UnwrapRef<typeof mode>;
      interval.value = props.data.notify_interval / 60;
    },
    {
      immediate: true,
    },
  );

  const intervalDesc = computed(() => {
    if (mode.value === 'standard') {
      return t('若产生相同的告警未确认或者未屏蔽，将按固定间隔重复通知');
    }
    return t('若产生相同的告警未确认或者未屏蔽，通知间隔将逐步递增');
  });

  const intervalIncreasingTip = computed(() => {
    const m = interval.value;
    return t('递增规则：{m1}分钟 → {m2}分钟 → {m3}分钟 → {m4}分钟 → ...（每次累加 {m} 分钟）', {
      m,
      m1: m,
      m2: m * 2,
      m3: m * 3,
      m4: m * 4,
    });
  });

  const handleChange = () => {
    emits('change');
  };

  defineExpose<Exposes>({
    getValue() {
      return {
        interval_notify_mode: mode.value,
        notify_interval: interval.value * 60,
      };
    },
  });
</script>

<style lang="less">
  .notice-interval {
    .notice-interval-row {
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 8px;

      .interval-select {
        width: 120px;
      }

      .interval-input {
        width: 100px;
      }

      .interval-text {
        font-size: 12px;
        color: #4d4f56;
      }
    }

    .interval-desc {
      font-size: 12px;
      line-height: 1.5;
      color: #979ba5;
    }

    .interval-tip {
      margin-top: 4px;
    }
  }
</style>
