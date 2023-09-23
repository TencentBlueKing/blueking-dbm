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
  <div class="title-spot item-title mt-24">
    {{ t('轮值排班') }}<span class="required" />
  </div>
  <DbOriginalTable
    class="table-box"
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { random } from '@utils';

  interface RowData {
    dateTime: string,
    timeRange: {
      id: string,
      value: string[];
    }[],
    peoples: string[],
  }

  const { t } = useI18n();

  const dateTimeRange = ref<[Date, Date]>([new Date(Date.now() - 24 * 60 * 60 * 1000), new Date()]);
  const copiedStr = ref('');
  const tableData = ref<RowData[]>([
    {
      dateTime: '2022-12-10',
      timeRange: [
        {
          id: random(),
          value: ['00:00:00', '23:59:59'],
        },
      ],
      peoples: ['ael', 'bellg', 'vellg', 'elang', 'ellang', 'elng', 'eang', 'ng'],
    },
    {
      dateTime: '2023-09-04',
      timeRange: [{
        id: random(),
        value: ['00:00:00', '23:59:59'],
      }],
      peoples: ['a', 'b', 'c', 'e', 'f', 'd', 'g', 'u'],
    },
    {
      dateTime: '2022-12-10',
      timeRange: [{
        id: random(),
        value: ['00:00:00', '23:59:59'],
      }],
      peoples: [],
    },
  ]);


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
        <div class={['time-group-box', { 'time-group-mutiple': data.timeRange.length > 1 }]}>
          {
            data.timeRange.map((item, innerIndex) => (
                <div class="time-item" key={item.id}>
                  <bk-time-picker v-model={item.value} clearable={false} type="timerange" />
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
      field: 'peoples',
      render: ({ data }: {data: RowData}) => (
        <div class="peoples">
          <bk-tag-input
            clearable={false}
            v-model={data.peoples}
            placeholder={t('请输入人员')}
            allow-create
            has-delete-icon
            collapse-tags
          />
          <div class="operate-box">
            {copiedStr.value !== '' && <db-icon
              class="operate-icon"
              type="paste"
              onClick={() => handleClickPaste(data)}/>}
            {data.peoples.length > 0 && <db-icon
              class="ml-10 operate-icon"
              type="copy-2"
              onClick={() => handleClickCopy(data)}/>}
          </div>
        </div>
        ),
    },
  ];

  const handleClickCopy = (row: RowData) => {
    copiedStr.value = row.peoples.join(',');
  };

  const handleClickPaste = (row: RowData) => {
    const oldArr = row.peoples;
    if (oldArr.length === 0) {
      Object.assign(row, {
        peoples: copiedStr.value.split(','),
      });
    } else {
      const addArr = copiedStr.value.split(',');
      const newArr = [...new Set([...oldArr, ...addArr])];
      Object.assign(row, {
        peoples: newArr,
      });
    }
  };

  const handleAddTime = (index: number) => {
    tableData.value[index].timeRange.push({
      id: random(),
      value: ['00:00:00', '23:59:59'],
    });
  };

  const handleDeleteTime = (outerIndex: number, innerIndex: number) => {
    tableData.value[outerIndex].timeRange.splice(innerIndex, 1);
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

.table-box {
  :deep(td) {
    background-color: #F5F7FA !important;
  }

  :deep(.peoples) {
    position: relative;
    display: flex;
    width: 100%;
    flex-wrap: wrap;

    .bk-tag-input {
      width: 100%;
    }

    .operate-box {
      position: absolute;
      top: 0;
      right: 0;
      display: flex;
      height: 100%;
      align-items: center;
      padding-right: 12px;

      .operate-icon {
        font-size: 18px;
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
        color: #979BA5;
        cursor: pointer;
      }
    }
  }
}
</style>
