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
  <div class="title">
    {{ t('轮值表') }}
  </div>
  <DbOriginalTable
    class="table-box"
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import MiniTag from '@components/mini-tag/index.vue';
  interface RowData {
    dateTime: string,
    timeRange: string[],
    peoples: string[],
  }

  const { t } = useI18n();

  const tableData = ref<RowData[]>([
    {
      dateTime: '2022-12-10',
      timeRange: ['07:00 ～14:00', '15:00 ～24:00'],
      peoples: ['ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang'],
    },
    {
      dateTime: '2023-09-04',
      timeRange: ['07:00 ～14:00', '15:00 ～24:00'],
      peoples: ['ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang'],
    },
    {
      dateTime: '2022-12-10',
      timeRange: ['07:00 ～14:00', '15:00 ～24:00'],
      peoples: ['ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang', 'ellanzhang'],
    },
  ]);

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
      render: ({ data }: {data: RowData}) => data.timeRange.join(','),
    },
    {
      label: t('轮值人员'),
      field: 'peoples',
      render: ({ data }: {data: RowData}) => <div class="peoples">{data.peoples.map(item => <bk-tag>{item}</bk-tag>)}</div>,
    },
  ];

</script>
<style lang="less" scoped>
.title {
  margin-top: 10px;
  margin-bottom: 17px;
  font-weight: 700;
  color: #313238;
}

.table-box {
  :deep(.peoples) {
    display: flex;
    flex-wrap: wrap;
  }
}
</style>
