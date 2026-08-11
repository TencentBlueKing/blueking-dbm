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
    :model="formModel">
    <BkFormItem
      :label="t('轮值起止时间')"
      property="dateTimeRange"
      required>
      <BkDatePicker
        ref="datePickerRef"
        v-model="formModel.dateTimeRange"
        append-to-body
        :clearable="false"
        style="width: 100%"
        type="daterange"
        @change="handleDatetimeRangeChange" />
    </BkFormItem>
    <BkFormItem
      :label="t('轮值排班')"
      property="tableData"
      required>
      <PrimaryTable
        :columns="columns"
        :data="formModel.tableData"
        row-key="dateTime" />
    </BkFormItem>
  </BkForm>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import type { DutyCustomItem } from '@services/model/monitor/duty-rule';
  import DutyRuleModel from '@services/model/monitor/duty-rule';

  import MemberSelector from '@components/db-member-selector/index.vue';

  import { getDiffDays, random } from '@utils';

  interface Props {
    data?: DutyRuleModel;
  }

  interface RowData {
    dateTime: string;
    members: string[];
    timeRange: {
      id: string;
      value: string[];
    }[];
  }

  interface Exposes {
    getValue: () => Promise<{
      duty_arranges: {
        date: string;
        members: string[];
        work_times: string[];
      }[];
      effective_time: string;
      end_time: string;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const formRef = ref();

  const formModel = reactive({
    dateTimeRange: undefined as [string, string] | undefined,
    tableData: [] as RowData[],
  });

  const columns: PrimaryTableCol[] = [
    {
      colKey: 'dateTime',
      title: t('轮值日期'),
      width: 120,
    },
    {
      cell: (_, { row, rowIndex }) => (
        <div class={{ 'time-group-box': true, 'time-group-mutiple': row.timeRange.length > 1 }}>
          {row.timeRange.map((item: RowData['timeRange'][number], innerIndex: number) => (
            <div
              key={item.id}
              class='time-item'>
              <bk-time-picker
                v-model={item.value}
                append-to-body
                clearable={false}
                format='HH:mm'
                style='width: 200px'
                type='timerange'
              />
              {innerIndex === 0 && (
                <db-icon
                  class='ml-10 icon'
                  type='plus-circle'
                  onClick={() => handleAddTime(rowIndex)}
                />
              )}
              {innerIndex !== 0 && (
                <db-icon
                  class='ml-10 icon'
                  type='minus-circle'
                  onClick={() => handleDeleteTime(rowIndex, innerIndex)}
                />
              )}
            </div>
          ))}
        </div>
      ),
      colKey: 'timeRange',
      title: t('轮值时间'),
      width: 250,
    },
    {
      cell: (_, { row, rowIndex }) => (
        <MemberSelector
          modelValue={row.members}
          onChange={(value: string[]) => handelPeopleChange(value, rowIndex)}
        />
      ),
      colKey: 'members',
      title: t('轮值人员'),
      width: 510,
    },
  ];

  watch(
    () => props.data,
    (data) => {
      if (data && data.category === 'regular') {
        formModel.dateTimeRange = [data.effective_time, data.end_time];
        formModel.tableData = (data.duty_arranges as DutyCustomItem[]).map((item) => ({
          dateTime: item.date,
          members: item.members,
          timeRange: item.work_times.map((i) => ({
            id: random(),
            value: i.split('--'),
          })),
        }));
      } else {
        formModel.tableData = [];
      }
    },
    {
      immediate: true,
    },
  );

  const handleDatetimeRangeChange = (value: [string, string]) => {
    formModel.dateTimeRange = value;
    const dateArr = getDiffDays(value[0], value[1]);
    formModel.tableData = dateArr.map((item) => ({
      dateTime: item,
      members: [],
      timeRange: [
        {
          id: random(),
          value: ['00:00', '23:59'],
        },
      ],
    }));
    nextTick(() => {
      formRef.value.validate('tableData');
    });
  };

  const handelPeopleChange = (value: string[], index: number) => {
    formModel.tableData[index].members = value;
  };

  const handleAddTime = (index: number) => {
    formModel.tableData[index].timeRange.push({
      id: random(),
      value: ['00:00', '23:59'],
    });
  };

  const handleDeleteTime = (outerIndex: number, innerIndex: number) => {
    formModel.tableData[outerIndex].timeRange.splice(innerIndex, 1);
  };

  defineExpose<Exposes>({
    async getValue() {
      await formRef.value.validate();
      return {
        duty_arranges: formModel.tableData.map((item) => ({
          date: item.dateTime,
          members: item.members,
          work_times: item.timeRange.map((data) => data.value.join('--')),
        })),
        effective_time: dayjs(formModel.dateTimeRange![0]).startOf('day').format('YYYY-MM-DD HH:mm:ss'),
        end_time: dayjs(formModel.dateTimeRange![1]).endOf('day').format('YYYY-MM-DD HH:mm:ss'),
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
</style>
<style lang="less">
  .time-group-box {
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
</style>
