<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkFormItem
    :label="t('执行模式')"
    required>
    <BkRadioGroup
      v-model="localMode"
      class="sql-execute-mode"
      @change="handleModeChange">
      <div class="item-box">
        <BkRadio label="manual">
          <div class="item-content">
            <DbIcon
              class="item-flag"
              type="account" />
            <div class="item-label">
              {{ t('手动执行') }}
            </div>
            <div>{{ t('单据审批通过之后_需要人工确认方可执行') }}</div>
          </div>
        </BkRadio>
      </div>
      <div class="item-box">
        <BkRadio label="timer">
          <div class="item-content">
            <DbIcon
              class="item-flag"
              type="timed-task" />
            <div class="item-label">
              {{ t('定时执行') }}
            </div>
            <div>{{ t('单据审批通过之后_定时执行_无需确认') }}</div>
          </div>
        </BkRadio>
      </div>
    </BkRadioGroup>
  </BkFormItem>
  <BkFormItem
    v-if="localMode === 'timer'"
    property="ticket_mode"
    required
    :rules="rules">
    <template #label>
      <span>{{ t('执行时间') }}</span>
      <span style="font-weight: normal; color: #979ba5">
        {{ t('在审批通过后_将会按照设置的时间定时执行_无需人工确认_如审批超时_需_人工确认_后才能执行') }}
      </span>
    </template>
    <div class="sql-execute-time-box">
      <TimeZonePicker style="width: 350px" />
      <div ref="timeRef">
        <BkDatePicker
          v-model="localTriggerTime"
          class="not-seconds-date-picker"
          :disabled-date="disableDate"
          type="datetime"
          @change="handleTriggerTimeChange" />
      </div>
    </div>
  </BkFormItem>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import { useTimeZoneFormat } from '@hooks';

  import TimeZonePicker from '@components/time-zone-picker/index.vue';

  interface Props {
    modelValue: {
      mode: string;
      trigger_time: string;
    };
  }

  interface Emits {
    (e: 'update:modelValue', value: Props['modelValue']): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const formatDateToUTC = useTimeZoneFormat();

  const disableDate = (date: number | Date) => Boolean(date && date.valueOf() < Date.now() - 86400000);

  const rules = [
    {
      validator: (value: Props['modelValue']) => !!value.trigger_time,
      message: t('定时执行时执行时间不能为空'),
      trigger: 'change',
    },
  ];

  const timeRef = ref();
  const localMode = ref(props.modelValue.mode);
  const localTriggerTime = ref(props.modelValue.trigger_time);

  watch(
    () => props.modelValue,
    () => {
      localMode.value = props.modelValue.mode;
      localTriggerTime.value = props.modelValue.trigger_time;
    },
  );

  const triggerChange = () => {
    nextTick(() => {
      emits('update:modelValue', {
        mode: localMode.value,
        trigger_time: formatDateToUTC(localTriggerTime.value),
      });
    });
  };

  const handleModeChange = (mode: string) => {
    localMode.value = mode;
    if (mode === 'timer') {
      const today = new Date();
      today.setSeconds(0);
      localTriggerTime.value = dayjs(today).format('YYYY-MM-DD HH:mm:ss');
      setTimeout(() => {
        timeRef.value.scrollIntoView();
      });
    } else {
      localTriggerTime.value = '';
    }
    triggerChange();
  };

  const handleTriggerTimeChange = (value: string) => {
    localTriggerTime.value = dayjs(value).format('YYYY-MM-DD HH:mm:ss');
    triggerChange();
  };
</script>
<style lang="less">
  .sql-execute-mode {
    flex-direction: column;

    .item-box {
      & ~ .item-box {
        margin-top: 20px;
      }

      .item-content {
        position: relative;
        padding-left: 25px;
        font-size: 12px;
        line-height: 20px;
        color: #63656e;
      }

      .item-flag {
        position: absolute;
        left: 3px;
        font-size: 18px;
        color: #979ba5;
      }

      .item-label {
        font-weight: bold;
      }

      .bk-radio {
        align-items: flex-start;

        .bk-radio-input {
          margin-top: 2px;
        }
      }
    }
  }

  .sql-execute-time-box {
    display: flex;
    align-items: center;
    gap: 8px;
  }
</style>
