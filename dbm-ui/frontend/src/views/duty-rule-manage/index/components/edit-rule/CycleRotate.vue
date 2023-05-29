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
  <BkForm
    ref="formRef"
    class="mt-24"
    form-type="vertical"
    :model="formModel"
    :rules="formRules">
    <BkFormItem
      :label="t('轮值人员')"
      property="peopleList"
      required>
      <span class="cycle-title-tip">（{{ t('排班时将会按照人员的顺序进行排班，可拖动 Tag 进行排序') }}）</span>
      <SortTagInput
        :list="formModel.peopleList"
        @change="handleSortTagInputChange" />
    </BkFormItem>
    <div class="cycle-duty-box">
      <BkFormItem
        :label="t('单次值班人数')"
        property="singleDutyPeoples"
        required>
        <BkInput
          v-model="formModel.singleDutyPeoples"
          class="input-item"
          :max="formModel.peopleList.length"
          type="number">
          <template #suffix>
            <span class="suffix-slot">人</span>
          </template>
        </BkInput>
      </BkFormItem>
      <BkFormItem
        :label="t('单班轮值天数')"
        property="sinlgeDutyDays"
        required>
        <BkInput
          v-model="formModel.sinlgeDutyDays"
          class="input-item"
          type="number">
          <template #suffix>
            <span class="suffix-slot">{{ t('天') }}</span>
          </template>
        </BkInput>
      </BkFormItem>
    </div>
  </BkForm>
  <div class="title-spot cycle-table-box mt-24">{{ t('轮值起止时间') }}<span class="required" /></div>
  <BkDatePicker
    ref="datePickerRef"
    append-to-body
    :clearable="false"
    :model-value="dateTimeRange"
    style="width: 100%"
    type="daterange"
    @change="handlerChangeDatetime" />
  <div class="cycle-time-select-box">
    <div class="select-item">
      <BkSelect
        v-model="dateSelect.date"
        :clearable="false">
        <BkOption
          v-for="(item, index) in dateList"
          :key="index"
          :label="item.label"
          :value="item.value" />
      </BkSelect>
    </div>
    <div
      v-if="dateSelect.date === 'weekly'"
      class="select-item">
      <BkSelect
        v-model="dateSelect.weekday"
        :clearable="false"
        multiple>
        <BkOption
          v-for="(item, index) in weekdayList"
          :key="index"
          :label="item.label"
          :value="item.value" />
      </BkSelect>
    </div>
    <div class="select-item">
      <div
        v-for="(item, index) in dateSelect.timeList"
        :key="item.id"
        class="time-select">
        <BkTimePicker
          v-model="item.value"
          :clearable="false"
          type="timerange" />
        <DbIcon
          v-if="index === 0"
          class="ml-10 icon"
          type="plus-circle"
          @click="handleAddTime" />
        <DbIcon
          v-else
          class="ml-10 icon"
          type="minus-circle"
          @click="() => handleDeleteTime(index)" />
      </div>
    </div>
  </div>
  <div class="cycle-preview-box">
    <div class="title">
      {{ t('排班预览') }}
    </div>
    <DbOriginalTable
      class="table-box"
      :columns="columns"
      :data="tableData" />
    <div
      v-if="showMoreTip"
      class="more-tip">
      {{ t('以此类推') }}...
    </div>
  </div>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { DutyCycleItem } from '@services/model/monitor/duty-rule';
  import DutyRuleModel from '@services/model/monitor/duty-rule';

  import {
    getDiffDays,
    random,
  } from '@utils';

  import SortTagInput from './SortTagInput.vue';

  interface RowData {
    dateTime: string,
    timeRange: string[],
    peoples: string[],
  }

  interface Props {
    data?: DutyRuleModel
  }

  interface Exposes {
    getValue: () => Promise<{
      effective_time: string,
      end_time: string,
      duty_arranges:{
        duty_number: number,
        duty_day: number,
        members: string[],
        work_type: string,
        work_days: number[],
        work_times:string[],
      }[],
    }>
  }

  const props = defineProps<Props>();

  function formatDate(date: string) {
    return dayjs(date).format('YYYY-MM-DD');
  }

  // 临时处理，待时间选择器修复后去除
  function transferToTimePicker(timeStr: string) {
    const arr = timeStr.split(':');
    if (arr.length === 2) {
      return `${timeStr}:00`;
    }
    return timeStr;
  }

  function initDateTimrRange() {
    return [
      formatDate(new Date().toISOString()),
      formatDate(new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString()),
    ] as [string, string];
  }

  function initDateSelect() {
    return ({
      date: 'daily',
      weekday: [] as number[],
      timeList: [{
        id: random(),
        value: ['00:00:00', '23:59:59'],
      }],
    });
  }

  const { t } = useI18n();

  const dateTimeRange = ref(initDateTimrRange());
  const dateSelect = ref(initDateSelect());
  const tableData = ref<RowData[]>([]);
  const formRef = ref();
  const showMoreTip = ref(false);
  const formModel = reactive({
    peopleList: [] as string[],
    singleDutyPeoples: 1,
    sinlgeDutyDays: 1,
  });

  const dateList = [
    {
      value: 'daily',
      label: t('每日'),
    },
    {
      value: 'weekly',
      label: t('每周'),
    },
  ];

  const weekdayList = [
    {
      value: 1,
      label: t('周一'),
    },
    {
      value: 2,
      label: t('周二'),
    },
    {
      value: 3,
      label: t('周三'),
    },
    {
      value: 4,
      label: t('周四'),
    },
    {
      value: 5,
      label: t('周五'),
    },
    {
      value: 6,
      label: t('周六'),
    },
    {
      value: 0,
      label: t('周日'),
    },
  ];

  const columns = [
    {
      label: t('日期'),
      field: 'dateTime',
      width: 120,
    },
    {
      label: t('时段'),
      field: 'timeRange',
      showOverflowTooltip: true,
      width: 200,
      render: ({ data }: {data: RowData}) => data.timeRange.join(','),
    },
    {
      label: t('轮值人员'),
      field: 'peoples',
      render: ({ data }: {data: RowData}) => <div class="peoples">{data.peoples.map(item => <bk-tag>{item}</bk-tag>)}</div>,
    },
  ];

  const formRules = {
    peopleList: [
      {
        validator: (value: string[]) => value.length > 0,
        message: t('轮值人员不能为空'),
        trigger: 'blur',
      },
    ],
    singleDutyPeoples: [
      {
        validator: (value: number) => value > 0,
        message: t('必须大于0'),
        trigger: 'blur',
      },
    ],
    sinlgeDutyDays: [
      {
        validator: (value: number) => value > 0,
        message: t('必须大于0'),
        trigger: 'blur',
      },
    ],
  };

  watch(
    [dateTimeRange, dateSelect, formModel],
    ([dateRange, data, formModel]) => {
      if (data.date && formModel.peopleList.length > 0) {
        const { singleDutyPeoples, sinlgeDutyDays, peopleList } = formModel;
        const days = sinlgeDutyDays;
        const peoplesCount = Math.min(singleDutyPeoples, peopleList.length);
        const startDate = formatDate(dateRange[0]);
        const endDate = formatDate(dateRange[1]);
        const dateArr = getDiffDays(startDate, endDate);
        const isSelectedWeekday = data.date !== 'daily' && data.weekday.length > 0;
        let daysCount = 0;
        let startIndex = 0;
        const targetArr = dateArr.reduce((results, item) => {
          if (isSelectedWeekday) {
            // 只取选中的星期几显示
            const weekday = dayjs(item).day();
            if (!data.weekday.includes(weekday)) {
              return results;
            }
          }
          if (daysCount < days) {
            daysCount = daysCount + 1;
          } else {
            startIndex = startIndex + peoplesCount;
            if (startIndex > peopleList.length) {
              startIndex = startIndex - peopleList.length;
            }
            daysCount = 1;
          }
          const dutyPeoples = getRangeList(peopleList, startIndex, peoplesCount);
          const obj = {
            dateTime: item,
            timeRange: dateSelect.value.timeList.map(item => item.value.join('~')),
            peoples: dutyPeoples,
          };
          results.push(obj);
          return results;
        }, [] as RowData[]);
        if (targetArr.length > 5) {
          showMoreTip.value = true;
          tableData.value = targetArr.slice(0, 5);
          return;
        }
        showMoreTip.value = false;
        tableData.value = targetArr;
      }
    }, {
      immediate: true,
      deep: true,
    },
  );

  watch(() => props.data, (data) => {
    if (data) {
      dateTimeRange.value = [data.effective_time, data.end_time];
      const arranges = data.duty_arranges as DutyCycleItem[];
      dateSelect.value.timeList = arranges[0].work_times.map(item => ({
        id: random(),
        value: item.split('--').map(time => transferToTimePicker(time)),
      }));
      formModel.sinlgeDutyDays = arranges[0].duty_day;
      formModel.singleDutyPeoples = arranges[0].duty_number;
      const allMembers = _.flatMap(arranges.map(item => item.members));
      const members = [...new Set(allMembers)];
      formModel.peopleList = members;
      const workType = arranges[0].work_type;
      dateSelect.value.date = workType;
      let workdays = arranges[0].work_days;
      workdays = workType === 'weekly' ? workdays.map(num => (num === 7 ? 0 : num)) : workdays;
      dateSelect.value.weekday = workdays;
    }
  }, {
    immediate: true,
  });

  const getRangeList = (arr: string[], startIndex: number, counts: number) => {
    const ret = [];
    let start = startIndex;
    for (let i = 0; i < counts; i++) {
      if (start >= arr.length) {
        start = 0;
      }
      ret.push(arr[start]);
      start = start + 1;
    }
    return ret;
  };

  const handleSortTagInputChange = (arr: string[]) => {
    formModel.peopleList = arr;
  };

  const handleAddTime = () => {
    dateSelect.value.timeList.push({
      id: random(),
      value: ['00:00:00', '23:59:59'],
    });
  };

  const handleDeleteTime = (index: number) => {
    dateSelect.value.timeList.splice(index, 1);
  };

  const handlerChangeDatetime = (range: [string, string]) => {
    dateTimeRange.value = range;
  };

  // 临时处理，待组件支持分钟后去除
  const splitTimeToMinute = (str: string) => {
    const strArr = str.split(':');
    if (strArr.length <= 2) {
      return str;
    }
    strArr.pop();
    return strArr.join(':');
  };

  defineExpose<Exposes>({
    async getValue() {
      await formRef.value.validate();
      let effctTime = dateTimeRange.value[0];
      effctTime = `${effctTime.split(' ')[0]} 00:00:00`;
      let endTime = dateTimeRange.value[1];
      endTime = `${endTime.split(' ')[0]} 00:00:00`;
      return {
        effective_time: effctTime,
        end_time: endTime,
        duty_arranges: tableData.value.map(item => ({
          duty_number: formModel.singleDutyPeoples,
          duty_day: formModel.sinlgeDutyDays,
          members: item.peoples,
          work_type: dateSelect.value.date,
          work_days: dateSelect.value.date === 'weekly' ? dateSelect.value.weekday.map(num => (num === 0 ? 7 : num)) : [],
          work_times: dateSelect.value.timeList.map(item => item.value.map(str => splitTimeToMinute(str)).join('--')),
        })),
      };
    },
  });
</script>
<style lang="less" scoped>
  .cycle-table-box {
    margin-bottom: 6px;
    font-weight: normal;
    color: #63656e;
  }

  .cycle-title-tip {
    position: absolute;
    top: -32px;
    left: 60px;
    font-size: 12px;
    color: #979ba5;
  }

  .cycle-duty-box {
    display: flex;
    width: 100%;
    justify-content: space-between;

    .bk-form-item {
      display: flex;
      width: 420px;
      flex-direction: column;
      gap: 6px;

      .input-item {
        height: 32px;

        :deep(.bk-input--number-control) {
          display: none;
        }
      }

      :deep(.suffix-slot) {
        width: 30px;
        height: 30px;
        line-height: 30px;
        text-align: center;
        background: #fafbfd;
        border-left: 1px solid #c4c6cc;
      }
    }
  }

  .cycle-time-select-box {
    display: flex;
    width: 100%;
    padding: 16px;
    margin-top: 12px;
    background: #f5f7fa;
    border-radius: 2px;
    gap: 8px;

    .select-item {
      display: flex;
      flex-direction: column;
      gap: 8px;

      .icon {
        font-size: 18px;
        cursor: pointer;
      }

      .time-select {
        display: flex;
        width: 100%;
        align-items: center;
      }
    }
  }

  .cycle-preview-box {
    width: 100%;
    padding: 12px 16px;
    margin-top: 16px;
    background: #f5f7fa;
    border-radius: 2px;

    .title {
      margin-bottom: 10px;
      font-size: 12px;
      font-weight: 700;
      color: #63656e;
    }

    .table-box {
      :deep(.peoples) {
        display: flex;
        flex-wrap: wrap;
      }
    }

    .more-tip {
      width: 100%;
      height: 42px;
      padding-left: 16px;
      font-size: 12px;
      line-height: 42px;
      color: #63656e;
      background: #fff;
    }
  }
</style>
