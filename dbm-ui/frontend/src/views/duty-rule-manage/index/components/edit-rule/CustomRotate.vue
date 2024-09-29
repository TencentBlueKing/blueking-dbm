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
  <div class="title-spot custom-item-title mt-24">{{ t('轮值起止时间') }}<span class="required" /></div>
  <BkDatePicker
    ref="datePickerRef"
    v-model="dateTimeRange"
    append-to-body
    :clearable="false"
    style="width: 100%"
    type="daterange"
    @change="handleDatetimeRangeChange" />
  <div class="title-spot custom-item-title mt-24">{{ t('轮值排班') }}<span class="required" /></div>
  <DbOriginalTable
    class="custom-table-box"
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import type { DutyCustomItem } from '@services/model/monitor/duty-rule';
  import DutyRuleModel from '@services/model/monitor/duty-rule';

  import MemberSelector from '@components/db-member-selector/index.vue';

  import { getDiffDays, random } from '@utils';

  interface Props {
    data?: DutyRuleModel;
  }

  interface RowData {
    dateTime: string,
    timeRange: {
      id: string,
      value: string[];
    }[],
    members: string[],
  }

  interface Exposes {
    getValue: () => {
      effective_time: string,
      end_time: string,
      duty_arranges:{
        date: string,
        work_times: string[],
        members: string[],
      }[],
    }
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dateTimeRange = ref<[string, string]>();
  const tableData = ref<RowData[]>([]);

  const columns = [
    {
      label: t('轮值日期'),
      field: 'dateTime',
      width: 120,
    },
    {
      label: t('轮值时间'),
      field: 'timeRange',
      showOverflowTooltip: true,
      width: 250,
      render: ({ data, index }: {data: RowData, index: number}) => (
        <div class={{ 'time-group-box': true, 'time-group-mutiple': data.timeRange.length > 1 }}>
          {
            data.timeRange.map((item, innerIndex) => (
              <div class="time-item" key={item.id}>
                <bk-time-picker
                  v-model={item.value}
                  clearable={false}
                  type="timerange"
                  append-to-body />
                  {innerIndex === 0 && <db-icon
                    class="ml-10 icon"
                    type="plus-circle"
                    onClick={() => handleAddTime(index)}/>}
                  {innerIndex !== 0 && <db-icon
                    class="ml-10 icon"
                    type="minus-circle"
                    onClick={() => handleDeleteTime(index, innerIndex)}/>}
              </div>
            ))
          }
        </div>
      ),
    },
    {
      label: t('轮值人员'),
      field: 'members',
      render: ({data, index}: {data: RowData, index: number}) =>(
        <MemberSelector
          modelValue={data.members}
          onChange={(value: string[]) => handelPeopleChange(value, index)} />
      ),
    },
  ];

  watch(() => props.data, (data) => {
    const transferToTimePicker = (timeStr: string) => {
      const arr = timeStr.split(':');
      if (arr.length === 2) {
        return `${timeStr}:00`;
      }
      return timeStr;
    }

    if (data && data.category === 'regular') {
      dateTimeRange.value = [data.effective_time, data.end_time];
      tableData.value = (data.duty_arranges as DutyCustomItem[]).map(item => ({
        dateTime: item.date,
        timeRange: item.work_times.map(i => ({
          id: random(),
          value: i.split('--').map(time => transferToTimePicker(time)),
        })),
        members: item.members,
      }));
    } else {
      tableData.value = []
    }
  }, {
    immediate: true,
  });


  const handleDatetimeRangeChange = (value: [string, string]) => {
    dateTimeRange.value = value;
    const dateArr = getDiffDays(value[0], value[1]);
    tableData.value = dateArr.map(item => ({
      dateTime: item,
      timeRange: [{
        id: random(),
        value: ['00:00:00', '23:59:59'],
      }],
      members: [],
    }));
  }

  const handelPeopleChange = (value: string[], index: number) => {
    tableData.value[index].members = value
  }

  const handleAddTime = (index: number) => {
    tableData.value[index].timeRange.push({
      id: random(),
      value: ['00:00:00', '23:59:59'],
    });
  };

  const handleDeleteTime = (outerIndex: number, innerIndex: number) => {
    tableData.value[outerIndex].timeRange.splice(innerIndex, 1);
  };


  defineExpose<Exposes>({
    getValue() {
      const splitTimeToMinute = (str: string) => {
        const strArr = str.split(':');
        if (strArr.length <= 2) {
          return str;
        }
        strArr.pop();
        return strArr.join(':');
      };
      return {
        effective_time: dayjs(dateTimeRange.value![0]).startOf('day').format('YYYY-MM-DD HH:mm:ss'),
        end_time: dayjs(dateTimeRange.value![1]).startOf('day').format('YYYY-MM-DD HH:mm:ss'),
        duty_arranges: tableData.value.map(item => ({
          date: item.dateTime,
          work_times: item.timeRange.map(data => data.value.map(str => splitTimeToMinute(str)).join('--')),
          members: item.members,
        })),
      };
    },
  });
</script>
<style lang="less" scoped>
  .custom-item-title {
    margin-bottom: 6px;
    font-weight: normal;
    color: #63656e;

    .title-tip {
      margin-left: 6px;
      font-size: 12px;
      color: #979ba5;
    }
  }

  .custom-table-box {
    :deep(td) {
      background-color: #f5f7fa !important;
    }

    :deep(.members) {
      position: relative;
      display: flex;
      width: 100%;
      flex-wrap: wrap;

      &:hover {
        .operate-box {
          .operate-icon {
            display: block !important;
          }
        }
      }

      .people-select {
        width: 100%;

        .angle-up {
          display: none !important;
        }
      }

      .bk-tag-input {
        width: 100%;
      }

      .operate-box {
        position: absolute;
        top: 0;
        right: 0;
        z-index: 9999;
        display: flex;
        height: 100%;
        padding-right: 12px;
        align-items: center;

        .operate-icon {
          display: none !important;
          font-size: 16px;
          color: #737987;
          cursor: pointer;
        }
      }
    }

    :deep(.time-group-mutiple) {
      padding: 10px 0;
    }

    :deep(.time-group-box) {
      display: flex;
      width: 100%;
      flex-flow: column wrap;
      gap: 8px;

      .time-item {
        display: flex;
        width: 100%;
        align-items: center;

        .icon {
          font-size: 18px;
          color: #979ba5;
          cursor: pointer;
        }
      }
    }
  }
</style>
