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
  <DbOriginalTable
    class="render-rotate-table-box"
    :columns="columns"
    :data="tableData"
    :max-height="300"
    @scroll-bottom="handleScrollToBottom" />
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import type {
    DutyCustomItem,
    DutyCycleItem,
  } from '@services/model/monitor/duty-rule';

  import MiniTag from '@components/mini-tag/index.vue';

  import { getDiffDays } from '@utils';

  import type { RowData as TableRowData } from './Index.vue';

  interface Props {
    data: TableRowData
  }

  interface RowData {
    dateTime: string,
    timeRange: string[],
    peoples: string[],
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isShowAllData = ref(false);

  const tableData = computed(() => {
    if (props.data.category === 'regular') {
      // 自定义轮值
      // eslint-disable-next-line max-len
      return (isShowAllData.value ? props.data.duty_arranges as DutyCustomItem[] : props.data.duty_arranges.slice(0, 8) as DutyCustomItem[]).map(item => ({
        dateTime: item.date,
        timeRange: item.work_times.map(data => data.replace('--', '~')),
        peoples: item.members,
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
        let weekday = dayjs(item).day();
        weekday = weekday === 0 ? 7 : weekday;
        if (dutyArranges[0].work_days.includes(weekday)) {
          return true;
        }
        return false;
      });
    }
    return dutyArranges.map((item, index) => ({
      dateTime: dateArr[index],
      timeRange: item.work_times.map(data => data.replace('--', '~')),
      peoples: item.members,
    }));
  });

  const columns = [
    {
      label: t('日期'),
      field: 'dateTime',
      width: 120,
      render: ({ data }: {data: RowData}) => {
        let tag = null;
        const today = dayjs(new Date()).format('YYYY-MM-DD');
        if (data.dateTime === today) {
          tag = <MiniTag content={t('今日')} theme="info" />;
        }
        return <div class="date">{data.dateTime}{tag}</div>;
      },
    },
    {
      label: t('时段'),
      field: 'timeRange',
      showOverflowTooltip: true,
      width: 200,
      render: ({ data }: {data: RowData}) => data.timeRange.join(' , '),
    },
    {
      label: t('轮值人员'),
      field: 'peoples',
      render: ({ data }: {data: RowData}) => <div class="peoples">{data.peoples.map(item => <bk-tag>{item}</bk-tag>)}</div>,
    },
  ];

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

.render-rotate-table-box {
  :deep(.peoples) {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
