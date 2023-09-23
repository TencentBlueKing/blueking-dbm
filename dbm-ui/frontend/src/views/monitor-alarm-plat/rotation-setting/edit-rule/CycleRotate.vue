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
  <div class="title-spot item-title mt-24">
    {{ t('轮值人员') }}<span class="required" />
    <span class="title-tip">（{{ t('排班时将会按照人员的顺序进行排班，可拖动 Tag 进行排序') }}）</span>
  </div>
  <SortTagInput @change="handleSortTagInputChange" />
  <div class="duty-box mt-24">
    <div class="duty-item">
      <div class="title-spot item-title">
        {{ t('单次值班人数') }}<span class="required" />
      </div>
      <BkInput
        v-model="singleDutyPeoples"
        class="input-item"
        type="number">
        <template #suffix>
          <span class="suffix-slot">人</span>
        </template>
      </BkInput>
    </div>
    <div class="duty-item">
      <div class="title-spot item-title">
        {{ t('单班轮值天数') }}<span class="required" />
      </div>
      <BkInput
        v-model="sinlgeDutyDays"
        class="input-item"
        type="number">
        <template #suffix>
          <span class="suffix-slot">{{ t('天') }}</span>
        </template>
      </BkInput>
    </div>
  </div>
  <div class="title-spot item-title mt-24">
    {{ t('轮值起止时间') }}<span class="required" />
  </div>
  <BkDatePicker
    ref="datePickerRef"
    append-to-body
    clearable
    :model-value="dateTimeRange"
    style="width:100%;"
    type="daterange"
    @change="handlerChangeDatetime"
    @pick-success="handleConfirmDatetime" />
  <div class="time-select-box">
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
      v-if="dateSelect.date === 'week'"
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
          :clearable="false"
          :model-value="item.value"
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
  <div class="preview-box">
    <div class="title">
      {{ t('排班预览') }}
    </div>
    <DbOriginalTable
      class="table-box"
      :columns="columns"
      :data="tableData" />
  </div>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import { getDiffDyas, random } from '@utils';

  import SortTagInput from './SortTagInput.vue';

  interface RowData {
    dateTime: string,
    timeRange: string[],
    peoples: string[],
  }

  const { t } = useI18n();

  const dateTimeRange = ref<[Date, Date]>([new Date(Date.now() - 24 * 60 * 60 * 1000 * 6), new Date()]);
  const dateSelect = ref({
    date: '',
    weekday: [] as number[],
    timeList: [{
      id: random(),
      value: ['00:00:00', '23:59:59'],
    }],
  });
  const peopleList = ref<string[]>([]);
  const singleDutyPeoples = ref();
  const sinlgeDutyDays = ref();

  const tableData = ref<RowData[]>([]);

  const dateList = [
    {
      value: 'day',
      label: '每日',
    },
    {
      value: 'week',
      label: '每周',
    },
  ];

  const weekdayList = [
    {
      value: 1,
      label: '周一',
    },
    {
      value: 2,
      label: '周二',
    },
    {
      value: 3,
      label: '每三',
    },
    {
      value: 4,
      label: '周四',
    },
    {
      value: 5,
      label: '每五',
    },
    {
      value: 6,
      label: '周六',
    },
    {
      value: 0,
      label: '每日',
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

  watch(
    [dateSelect, singleDutyPeoples, sinlgeDutyDays, peopleList],
    ([data, singleDutyPeoples, sinlgeDutyDays, peopleList]) => {
      if (data.date) {
        const days = Number(sinlgeDutyDays);
        const peoplesCount = Math.min(Number(singleDutyPeoples), peopleList.length);
        const startDate = formatDate(dateTimeRange.value[0]);
        const endDate = formatDate(dateTimeRange.value[1]);
        const dateArr = getDiffDyas(startDate, endDate);
        const isSelectedWeekday = data.date !== 'day' && data.weekday.length > 0;
        let daysCount = 0;
        let startIndex = 0;
        tableData.value = dateArr.reduce((results, item) => {
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
      }
    }, {
      immediate: true,
      deep: true,
    },
  );

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

  const formatDate = (date: Date) => dayjs(date).format('YYYY-MM-DD');

  const handleSortTagInputChange = (arr: string[]) => {
    peopleList.value = arr;
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

  const handlerChangeDatetime = (range: [Date, Date]) => {
    dateTimeRange.value = range;
  };

  const handleConfirmDatetime = () => {
    console.log('select: ', dateTimeRange.value);
  };

</script>
<style lang="less" scoped>
.item-title {
  margin-bottom: 6px;
  font-weight: normal;
  color: #63656E;

  .title-tip {
    margin-left: 6px;
    font-size: 12px;
    color: #979BA5;
  }
}

.duty-box {
  display: flex;
  width: 100%;
  justify-content: space-between;

  .duty-item {
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
      background: #FAFBFD;
      border-left: 1px solid #C4C6CC;
    }
  }
}

.time-select-box {
  display: flex;
  width: 100%;
  padding: 16px;
  margin-top: 12px;
  background: #F5F7FA;
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

.preview-box {
  width: 100%;
  padding: 12px 16px;
  margin-top: 16px;
  background: #F5F7FA;
  border-radius: 2px;

  .title {
    margin-bottom: 10px;
    font-size: 12px;
    font-weight: 700;
    color: #63656E;
  }

  .table-box {
    :deep(.peoples) {
      display: flex;
      flex-wrap: wrap;
    }
  }
}
</style>
