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
  <BkFormItem
    class="notice-mothod"
    :label="t('通知方式')"
    property="method"
    required
    :rules="rules">
    <BkTab
      v-model:active="active"
      addable
      type="border-card">
      <template #add>
        <BkButton
          v-bk-tooltips="{
            content: t('已配置全天24小时生效时段，无需额外添加生效时段'),
            disabled: addPanelTipDiabled
          }"
          :disabled="!addPanelTipDiabled"
          text
          theme="primary"
          @click="addPanel">
          <DbIcon type="add" />
          {{ t('生效时段') }}
        </BkButton>
      </template>
      <BkTabPanel
        v-for="(item, index) in methods"
        :key="item.name"
        :name="item.name">
        <template #label>
          <BkTimePicker
            append-to-body
            format="HH:mm"
            :open="item.open"
            type="timerange"
            :value="item.timeRange"
            @change="(date: string[]) => handleTimeChange(date, index)">
            <template #trigger>
              <BkButton
                text
                :theme="item.name === active ? 'primary' : undefined"
                @click="handleTabClick(index)">
                <DbIcon type="clock" />
                <span class="ml-8">{{ timeArrayFormatter(item.timeRange) }}</span>
                <BkButton
                  class="tab-delete-btn ml-8"
                  text
                  theme="danger"
                  @click.stop="handleTabDelete(index)">
                  <DbIcon type="delete" />
                </BkButton>
              </bkbutton>
            </template>
          </BkTimePicker>
        </template>
        <template #panel>
          <div class="tab-penel-box">
            <p class="notice-text">
              {{ t('每个告警级别至少选择一种通知方式') }}
            </p>
            <div class="table">
              <div class="table-row tabel-head-row">
                <div
                  v-for="headItem in head"
                  :key="headItem.label"
                  class="table-row-item table-row-head-item"
                  :class="{
                    'table-row-type': headItem.type,
                    'table-row-input': headItem.input
                  }">
                  <img
                    v-if="headItem.icon"
                    height="20"
                    :src="`data:image/png;base64,${headItem.icon}`"
                    width="20">
                  <span
                    class="ml-4"
                    :class="{ 'label-bold': headItem.bold }">
                    {{ headItem.label }}
                  </span>
                </div>
              </div>
              <div
                v-for="(dataItem, dataIndex) in item.dataList"
                :key="dataIndex"
                class="table-row table-content-row">
                <div
                  class="table-row-item table-row-type">
                  <div
                    class="text"
                    :class="[`${dataItem.type}`]">
                    {{ dataItem.label }}
                  </div>
                </div>
                <div
                  v-for="(checkboxItem, checkboxIndex) in dataItem.checkboxArr"
                  :key="checkboxIndex"
                  class="table-row-item">
                  <BkCheckbox v-model="checkboxItem.checked" />
                </div>
                <div
                  v-for="(inputItem, inputIndex) in dataItem.inputArr"
                  :key="inputIndex"
                  class="table-row-item table-row-input">
                  <BkInput
                    v-model="inputItem.value"
                    class="mb10"
                    :placeholder="t('请输入群ID')" />
                </div>
              </div>
            </div>
          </div>
        </template>
      </BkTabPanel>
    </BkTab>
  </BkFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAlarmGroupNotifyList } from '../common/services';
  import type {
    AlarmGroupDetail,
    AlarmGroupNotice,
    AlarmGroupNotify,
  } from '../common/types';

  interface Props {
    type: 'add' | 'edit' | 'copy' | '',
    details: AlarmGroupDetail
  }

  interface Exposes {
    getSubmitData: () => AlarmGroupNotice[];
  }

  interface LevelMapItem {
    label: string,
    type: 'default' | 'warning' | 'error',
    level: 3 | 2 | 1
  }

  type AlarmGroupNotifyDisplay = Omit<AlarmGroupNotify, 'is_active'>

  interface PanelCheckbox extends AlarmGroupNotifyDisplay {
    checked: boolean,
  }

  interface PanelInput extends AlarmGroupNotifyDisplay {
    value: string
  }

  interface TableHead {
    label: string,
    bold?: boolean,
    type?: boolean,
    icon?: string,
    input?: boolean
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const methods = ref([] as {
    name: string,
    open: boolean,
    timeRange: string[],
    dataList: ({
      checkboxArr: PanelCheckbox[],
      inputArr: PanelInput[]
    } & LevelMapItem)[]
  }[]);
  const active = ref('');

  const isIntervalsFullDay = (minutesIntervals: {
    start: number,
    end: number,
  }[]) =>  {
    if (minutesIntervals.length === 0) {
      return false;
    }

    // 合并有交集的时间段
    const mergedIntervals = [];

    minutesIntervals.sort((a, b) => a.start - b.start);

    let currentInterval = minutesIntervals[0];
    for (let i = 1; i < minutesIntervals.length; i++) {
      const nextInterval = minutesIntervals[i];

      if (currentInterval.end >= nextInterval.start) {
        currentInterval.end = Math.max(currentInterval.end, nextInterval.end);
      } else {
        mergedIntervals.push(currentInterval);
        currentInterval = nextInterval;
      }
    }
    mergedIntervals.push(currentInterval);

    // 计算合并后的时间段总时长是否为一天的总分钟数
    const totalMinutes = mergedIntervals.reduce((total, interval) => total + (interval.end - interval.start), 0);

    return totalMinutes === 24 * 60 - 1;
  };

  const inputTypes = ['wxwork-bot', 'bkchat'];

  const addPanelTipDiabled = computed(() => {
    const timeArr = methods.value.map((item) => {
      const [start, end] = item.timeRange;
      const [startHour, startMinute] = start.split(':');
      const [endHour, endMinute] = end.split(':');

      return {
        start: Number(startHour) * 60 +  Number(startMinute),
        end: Number(endHour) * 60 + Number(endMinute),
      };
    });

    return !isIntervalsFullDay(timeArr);
  });

  let head: TableHead[] = [
    {
      label: t('告警级别'),
      bold: true,
      type: true,
    },
  ];

  const levelMap: Record<number, LevelMapItem> = {
    3: {
      label: t('提醒'),
      type: 'default',
      level: 3,
    },
    2: {
      label: t('预警'),
      type: 'warning',
      level: 2,
    },
    1: {
      label: t('致命'),
      type: 'error',
      level: 1,
    },
  };

  const panelInitData: {
    checkboxArr: PanelCheckbox[],
    inputArr: PanelInput[]
  } = {
    checkboxArr: [],
    inputArr: [],
  };

  const addPanel = () => {
    const name = Math.random()
      .toString(16)
      .substring(4, 10);

    methods.value.push({
      name,
      open: false,
      timeRange: ['00:00', '23:59'],
      dataList: [
        {
          ...levelMap[3],
          checkboxArr: _.cloneDeep(panelInitData.checkboxArr),
          inputArr: _.cloneDeep(panelInitData.inputArr),
        },
        {
          ...levelMap[2],
          checkboxArr: _.cloneDeep(panelInitData.checkboxArr),
          inputArr: _.cloneDeep(panelInitData.inputArr),
        },
        {
          ...levelMap[1],
          checkboxArr: _.cloneDeep(panelInitData.checkboxArr),
          inputArr: _.cloneDeep(panelInitData.inputArr),
        },
      ],
    });

    active.value = name;
  };

  useRequest(getAlarmGroupNotifyList, {
    onSuccess(res) {
      const checkboxHead: TableHead[] = [];
      const inputHead: TableHead[] = [];

      res.forEach((item) => {
        const { type, label, is_active: isActive, icon } = item;

        if (isActive) {
          if (inputTypes.includes(type)) {
            panelInitData.inputArr.push({
              type,
              label,
              icon,
              value: '',
            });

            inputHead.push({
              label,
              icon,
              input: true,
            });
          } else {
            panelInitData.checkboxArr.push({
              type,
              label,
              icon,
              checked: false,
            });

            checkboxHead.push({
              label,
              icon,
            });
          }
        }
      });

      head = [...head, ...checkboxHead, ...inputHead];

      setInitPanelList();
    },
  });

  const setInitPanelList = () => {
    const { type, details } = props;

    if (type === 'add') {
      addPanel();
    } else if (type === 'edit' || type === 'copy') {
      methods.value = details.alert_notice.map((item) => {
        const name = Math.random()
          .toString(16)
          .substring(4, 10);

        const dataList = item.notify_config.map((configItem) => {
          const checkboxArr = _.cloneDeep(panelInitData.checkboxArr);
          const inputArr = _.cloneDeep(panelInitData.inputArr);

          configItem.notice_ways.forEach((wayItem) => {
            if (inputTypes.includes(wayItem.name)) {
              const idx = inputArr.findIndex(inputItem => inputItem.type === wayItem.name);

              if (idx > -1) {
                inputArr[idx].value = wayItem.receivers?.join(',') as string;
              }
            } else {
              const idx = checkboxArr.findIndex(checkboxItem => checkboxItem.type === wayItem.name);

              if (idx > -1) {
                checkboxArr[idx].checked = true;
              }
            }
          });

          return {
            ...levelMap[configItem.level],
            checkboxArr,
            inputArr,
          };
        });

        return {
          name,
          open: false,
          timeRange: item.time_range.split('--'),
          dataList,
        };
      });

      active.value = methods.value[0].name;
    }
  };

  const rules = [
    {
      required: true,
      message: t('每个告警级别至少选择一种通知方式'),
      validator: () => methods.value.every(item => item.dataList.every(dataItem => (dataItem.checkboxArr.some(checkItem => checkItem.checked) || dataItem.inputArr.some(inputItem => inputItem.value !== '')))),
    },
  ];

  watch(active, () => {
    methods.value.forEach(item => Object.assign(item, { open: false }));
  });

  const handleTimeChange = (date: string[], index: number) => {
    methods.value[index].timeRange = date;
  };

  const handleTabClick = (index: number) => {
    const item = methods.value[index];

    if (item.name === active.value) {
      item.open = !item.open;
    }
  };

  const handleTabDelete = (index: number) => {
    methods.value.splice(index, 1);
  };

  const timeArrayFormatter = (timeArr: string[]): string =>  {
    if (timeArr && timeArr.length === 2) {
      const [start, end] = timeArr;

      return `${start} ~ ${end}`;
    }

    return '';
  };

  defineExpose<Exposes>({
    getSubmitData() {
      const submitData = methods.value.map((item) => {
        const {
          timeRange,
          dataList,
        } = item;

        return {
          time_range: timeRange.join('--'),
          notify_config: dataList.map((dataItem) => {
            const {
              checkboxArr,
              inputArr,
              level,
            } = dataItem;

            const noticeWaysCheck = checkboxArr.reduce((prev, current) => {
              if (current.checked) {
                prev.push({
                  name: current.type,
                });
              }
              return prev;
            }, [] as {
              name: string,
              receivers?: string[]
            }[]);

            const noticeWaysInput = inputArr.reduce((prev, current) => {
              if (current.value !== '') {
                prev.push({
                  name: current.type,
                  receivers: current.value.split(','),
                });
              }

              return prev;
            }, [] as {
              name: string,
              receivers?: string[]
            }[]);

            return {
              level,
              notice_ways: [...noticeWaysCheck, ...noticeWaysInput],
            };
          }),
        };
      });

      return submitData;
    },
  });
</script>

<style lang="less" scoped>
  .notice-mothod {
    :deep(.bk-date-picker) {
      width: 136px;
    }

    .tab-delete-btn {
      font-size: 18px;
      display: none;
    }

    :deep(.bk-tab-header-item:hover) {
      .tab-delete-btn {
        display: inherit;
      }
    }

    .tab-penel-box {
      padding: 0 24px 8px;
    }

    .notice-text {
      font-size: 12px;
      color: @gray-color;
    }

    .table {
      border: 1px solid #DCDEE5;
      border-bottom: none;
      border-radius: 2px;
      width: 100%;
      overflow: auto;

      .table-row {
        display: flex;

        .table-row-item {
          min-width: 120px;
          flex: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 0 12px;
          border-bottom: 1px solid #DCDEE5;
          flex-shrink: 0;

          &:not(:last-child) {
            border-right: 1px solid #DCDEE5;
          }
        }

        .table-row-head-item {
          background-color: #FAFBFD;
        }

        .table-row-type {
          width: 120px;

          .text {
            font-size: 12px;
            line-height: 18px;
            padding-left: 6px;
            border-radius: 1px;
          }
          .default {
            border-left: 4px solid @primary-color;
          }

          .warning {
            border-left: 4px solid @warning-color;
          }

          .error {
            border-left: 4px solid @danger-color;
          }
        }
        .table-row-input {
          flex: 1;
          min-width: 300px;
        }

        .table-row-icon {
          font-size: 16px;
        }

        .label-bold {
          font-weight: bold;
        }
      }

      .tabel-head-row {
        height: 42px;
      }

      .table-content-row {
        height: 52px;
      }
    }
  }
</style>
