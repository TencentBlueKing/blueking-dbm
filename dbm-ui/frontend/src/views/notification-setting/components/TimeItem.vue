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
  <DbFormItem
    class="notification-setting-time-item"
    :label="t('发送时间')"
    property="cron"
    required
    :rules="timeDataRules">
    <BkSelect
      v-model="timeData.typeValue"
      :clearable="false">
      <BkOption
        v-for="(item, index) in typeOptions"
        :key="index"
        :label="item.label"
        :value="item.value" />
    </BkSelect>
    <BkSelect
      v-if="timeData.typeValue === 'week'"
      v-model="timeData.weekValue"
      class="group-item"
      :clearable="false"
      multiple>
      <BkOption
        v-for="(item, index) in weekOptions"
        :key="index"
        :label="item.label"
        :value="item.value" />
    </BkSelect>
    <BkSelect
      v-if="timeData.typeValue === 'month'"
      v-model="timeData.monthValue"
      class="group-item date-selector"
      :clearable="false"
      multiple
      :popover-options="{
        extCls: 'notification-setting-time-item-date-selector-popover',
      }">
      <BkOption
        v-for="(item, index) in monthOptions"
        :key="index"
        :label="item.label"
        :value="item.value">
        {{ item.value }}
      </BkOption>
    </BkSelect>
    <BkTimePicker
      v-model="timeData.timeValue"
      append-to-body
      class="group-item datavalue-selector"
      :clearable="false"
      :editable="false"
      format="HH:mm"
      :show-date="false"
      type="time" />
  </DbFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    data: {
      day_of_month: string;
      day_of_week: string;
      hour: string;
      minute: string;
    };
  }

  interface Exposes {
    getValue: () => Props['data'];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const initData = () => ({
    monthValue: [] as string[],
    timeValue: '00:00',
    typeValue: 'day',
    weekValue: [] as string[],
  });

  const timeDataRules = [
    {
      message: t('请选择'),
      required: true,
      validator() {
        const { monthValue, timeValue, typeValue, weekValue } = timeData;

        if (typeValue === 'day') {
          return timeValue !== '';
        }
        if (typeValue === 'week') {
          return weekValue.length > 0 && timeValue !== '';
        }
        if (typeValue === 'month') {
          return monthValue.length > 0 && timeValue !== '';
        }

        return true;
      },
    },
  ];

  const monthOptions = Array.from({ length: 31 }, () => '').map((_, index) => ({
    label: `${index + 1}${t('号')}`,
    value: `${index + 1}`,
  }));

  const typeOptions = ref([
    {
      label: t('每天'),
      value: 'day',
    },
    {
      label: t('每周'),
      value: 'week',
    },
    {
      label: t('每月'),
      value: 'month',
    },
  ]);

  const weekOptions = ref([
    {
      label: t('周一'),
      value: '1',
    },
    {
      label: t('周二'),
      value: '2',
    },
    {
      label: t('周三'),
      value: '3',
    },
    {
      label: t('周四'),
      value: '4',
    },
    {
      label: t('周五'),
      value: '5',
    },
    {
      label: t('周六'),
      value: '6',
    },
    {
      label: t('周日'),
      value: '7',
    },
  ]);

  const timeData = reactive(initData());

  watch(
    () => props.data,
    () => {
      const { day_of_month: dayOfMonth, day_of_week: dayOfWeek, hour, minute } = props.data;
      const formDataRes = initData();

      formDataRes.timeValue = `${hour}:${minute}`;

      if (dayOfWeek !== '*') {
        formDataRes.weekValue = dayOfWeek.split(',');
        formDataRes.typeValue = 'week';
      } else if (dayOfMonth !== '*') {
        formDataRes.monthValue = dayOfMonth.split(',');
        formDataRes.typeValue = 'month';
      }

      Object.assign(timeData, formDataRes);
    },
  );

  defineExpose<Exposes>({
    getValue() {
      const { monthValue, timeValue, typeValue, weekValue } = timeData;
      const [hour = '', minute = ''] = timeValue.split(':');
      const value = {
        day_of_month: '*',
        day_of_week: '*',
        hour,
        minute,
      };

      if (typeValue === 'week') {
        value.day_of_week = weekValue.join(',');
      } else if (typeValue === 'month') {
        value.day_of_month = monthValue.join(',');
      }
      return value;
    },
  });
</script>

<style lang="less">
  .notification-setting-time-item {
    .bk-form-content {
      display: flex;
    }

    .group-item {
      margin-left: 4px;
    }

    .date-selector {
      width: 260px;
    }

    .datavalue-selector {
      width: 150px;
    }
  }

  .notification-setting-time-item-date-selector-popover {
    .bk-select-options {
      display: flex;
      flex-wrap: wrap;
      padding: 4px 12px !important;
    }

    .bk-select-option {
      justify-content: center;
      width: calc(100% / 7);
      padding: 0 !important;
    }

    .bk-select-selected-icon {
      display: none !important;
    }
  }
</style>
