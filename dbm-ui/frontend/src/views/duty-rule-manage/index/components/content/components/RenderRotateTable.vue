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
  <div class="render-rotate-table-title">
    {{ t('轮值表') }}
  </div>
  <BkTable
    :data="tableData"
    :max-height="300"
    :show-overflow="false"
    @scroll-bottom="handleScrollToBottom">
    <BkTableColumn
      field="dateTime"
      :label="t('日期')"
      :min-width="120">
      <template #default="{ data: rowData }: { data: RowData }">
        <div class="date">
          {{ rowData.dateTime }}
          <MiniTag
            v-if="rowData.dateTime === dayjs(new Date()).format('YYYY-MM-DD')"
            :content="t('今日')"
            theme="info" />
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="timeRange"
      :label="t('时段')"
      :min-width="200" />
    <BkTableColumn
      field="peoples"
      :label="t('轮值人员')">
      <template #default="{ data: rowData }: { data: RowData }">
        <div class="peoples">
          <BkTag
            v-for="item in rowData.peoples"
            :key="item">
            {{ item }}
          </BkTag>
        </div>
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import type { DutyCustomItem, DutyCycleItem } from '@services/model/monitor/duty-rule';
  import DutyRuleModel from '@services/model/monitor/duty-rule';

  import MiniTag from '@components/mini-tag/index.vue';

  import { getDiffDays } from '@utils';

  interface Props {
    data: DutyRuleModel;
  }

  interface RowData {
    dateTime: string;
    peoples: string[];
    timeRange: string[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShowAllData = ref(false);

  const tableData = computed(() => {
    if (props.data.category === 'regular') {
      // 自定义轮值
      return (
        isShowAllData.value
          ? (props.data.duty_arranges as DutyCustomItem[])
          : (props.data.duty_arranges.slice(0, 8) as DutyCustomItem[])
      ).map((item) => ({
        dateTime: item.date,
        peoples: item.members,
        timeRange: item.work_times.map((data) => data.replace('--', '~')),
      }));
    }
    // 周期轮值
    const startDate = props.data.effective_time.split(' ')[0];
    const endDate = props.data.end_time.split(' ')[0];
    let dateArr = getDiffDays(startDate, endDate);
    const dutyArranges = props.data.duty_arranges as DutyCycleItem[];
    if (dutyArranges[0].work_type !== 'daily') {
      // 按周
      dateArr = dateArr.filter((item) => {
        let weekday = dayjs(item).day() as number;
        weekday = weekday === 0 ? 7 : weekday;
        if (dutyArranges[0].work_days.includes(weekday)) {
          return true;
        }
        return false;
      });
    }
    return dutyArranges.map((item, index) => ({
      dateTime: dateArr[index],
      peoples: item.members.slice(0, item.duty_number),
      timeRange: item.work_times.map((data) => data.replace('--', '~')),
    }));
  });

  const handleScrollToBottom = () => {
    if (props.data.duty_arranges.length > 8) {
      isShowAllData.value = true;
    }
  };
</script>
<style lang="less" scoped>
  .render-rotate-table-title {
    margin-top: 10px;
    margin-bottom: 17px;
    font-weight: 700;
    color: #313238;
  }
</style>
