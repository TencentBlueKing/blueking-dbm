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
  <div class="health-report-toolbar">
    <span class="health-report-toolbar-label">{{ t('数据日期') }}</span>
    <span v-bk-tooltips="prevDate ? t('上一期（{date}）', { date: prevDate }) : t('已是最早一期')">
      <BkButton
        :disabled="!prevDate"
        @click="handleChange(prevDate)">
        ‹ {{ t('上一期') }}
      </BkButton>
    </span>
    <span
      v-bk-tooltips="{
        content: reportToTime
          ? t('生成时间：{time}；报告每日约 06:00 生成上一自然日数据，未生成的日期在日历中置灰', {
              time: utcDisplayTime(reportToTime),
            })
          : t('该集群暂无报告'),
        disabled: !reportToTime && !isEmpty,
      }"
      class="ml-8 mr-8">
      <BkDatePicker
        :clearable="false"
        :disabled="isEmpty"
        :disabled-date="disableDate"
        :model-value="date"
        :placeholder="t('暂无报告')"
        style="width: 160px"
        type="date"
        @change="handleDateChange" />
    </span>
    <span v-bk-tooltips="nextDate ? t('下一期（{date}）', { date: nextDate }) : t('已是最新一期')">
      <BkButton
        :disabled="!nextDate"
        @click="handleChange(nextDate)">
        {{ t('下一期') }} ›
      </BkButton>
    </span>
    <span
      v-if="missedDays >= 2"
      class="health-report-toolbar-stale ml-16">
      {{ t('{n} 天未生成新报告', { n: missedDays }) }}
    </span>
    <BkButton
      v-if="latestDate && date !== latestDate"
      v-bk-tooltips="t('回到最新（{date}）', { date: latestDate })"
      class="ml-16"
      text
      theme="primary"
      @click="handleChange('')">
      {{ t('回到最新') }}
    </BkButton>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { utcDisplayTime } from '@utils';

  interface Props {
    // 升序排列的有报告日期
    availableDates: string[];
    // 当前打开的数据日期
    date: string;
    latestDate: string;
    reportToTime: string;
  }

  // 传空字符串表示回到最新一份
  type Emits = (e: 'change', value: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isEmpty = computed(() => props.availableDates.length < 1);
  const availableDateSet = computed(() => new Set(props.availableDates));
  // 当前日期不在列表中（停在该日空态）时同样按前后最近一天步进
  const prevDate = computed(() => (props.date ? _.findLast(props.availableDates, (item) => item < props.date) : ''));
  const nextDate = computed(() => (props.date ? props.availableDates.find((item) => item > props.date) : ''));
  // 缺期天数只取决于最新一天，与当前打开哪一期无关
  const missedDays = computed(() =>
    props.latestDate ? dayjs().startOf('day').diff(dayjs(props.latestDate), 'day') - 1 : 0,
  );

  const disableDate = (date?: Date | number) => !availableDateSet.value.has(dayjs(date).format('YYYY-MM-DD'));

  const handleChange = (value = '') => {
    emits('change', value);
  };

  const handleDateChange = (value: string) => {
    if (value && value !== props.date) {
      handleChange(value);
    }
  };
</script>
<style lang="less">
  .health-report-toolbar {
    display: flex;
    align-items: center;
    padding-bottom: 16px;
    font-size: 12px;

    .health-report-toolbar-label {
      margin-right: 8px;
      color: #313238;
    }

    .health-report-toolbar-stale {
      color: #ff9c01;
    }
  }
</style>
