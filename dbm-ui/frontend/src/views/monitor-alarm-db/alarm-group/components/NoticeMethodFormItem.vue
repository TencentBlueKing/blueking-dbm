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
    :rules="methodRules">
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
          class="add-panel-button"
          :disabled="!addPanelTipDiabled"
          text
          theme="primary"
          @click="addPanel">
          <DbIcon type="add" />
          {{ t('生效时段') }}
        </BkButton>
      </template>
      <BkTabPanel
        v-for="(item, index) in panelList"
        :key="item.name"
        :name="item.name">
        <template #label>
          <BkTimePicker
            :ref="(el: TimePickerRef) => {
              setTimePickerRef(el, index)
              return void 0
            }"
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
            <div class="panel-item-table">
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
                    class="table-row-type-text"
                    :class="[`table-row-type-text-${dataItem.type}`]">
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
    <div
      :class="{'notice-mothod-open-mask': isTimePickerOpen}"
      @click="handleOpenMackClick" />
  </BkFormItem>
</template>

<script setup lang="ts">
  import BkTimePicker from 'bkui-vue/lib/time-picker';
  import _ from 'lodash';
  import type ComponentPublicInstance from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    getAlarmGroupList,
    getAlarmGroupNotifyList,
  } from '@services/source/monitorNoticeGroup';

  import { messageWarn } from '@utils';

  interface Props {
    type: 'add' | 'edit' | 'copy' | '',
    details: AlarmGroupDetail
  }

  interface Exposes {
    getSubmitData: () => AlarmGroupNotice[];
  }

  type TimePickerRef = ComponentPublicInstance<typeof BkTimePicker>
  type AlarmGroupDetail = ServiceReturnType<typeof getAlarmGroupList>['results'][number]['details']
  type AlarmGroupNotice = AlarmGroupDetail['alert_notice'][number]
  type AlarmGroupNotifyDisplay = Omit<ServiceReturnType<typeof getAlarmGroupNotifyList>[number], 'is_active'>

  interface LevelMapItem {
    label: string,
    type: 'default' | 'warning' | 'error',
    level: 3 | 2 | 1
  }

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

  const timeRangeFormatter = (timeRange: string[]) => {
    const [start, end] = timeRange;
    const [startHour, startMinute] = start.split(':');
    const [endHour, endMinute] = end.split(':');

    return {
      start: Number(startHour) * 60 + Number(startMinute),
      end: Number(endHour) * 60 + Number(endMinute),
    };
  };

  const { t } = useI18n();

  const inputTypes = ['wxwork-bot', 'bkchat'];

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

  const methodRules = [
    {
      required: true,
      message: t('每个告警级别至少选择一种通知方式'),
      validator: () => panelList.value.every(item => item.dataList.every(dataItem => (dataItem.checkboxArr.some(checkItem => checkItem.checked) || dataItem.inputArr.some(inputItem => inputItem.value !== '')))),
    },
  ];

  const timePickerRefs: Record<number, TimePickerRef> = {};
  let currentPanelIndex = -1;
  let currentPanelTimeRange:string[] = [];

  const active = ref('');
  const panelList = ref<{
    name: string,
    open: boolean,
    timeRange: string[],
    dataList:({
      checkboxArr: PanelCheckbox[],
      inputArr: PanelInput[]
    } & LevelMapItem)[]
  }[]>([]);

  const addPanelTipDiabled = computed(() => {
    const timeArr = panelList.value.map(item => timeRangeFormatter(item.timeRange));

    return !isIntervalsFullDay(timeArr);
  });

  const isTimePickerOpen = computed(() => panelList.value.some(panelItem => panelItem.open));

  useRequest(getAlarmGroupNotifyList, {
    onSuccess(notifyList) {
      const checkboxHead: TableHead[] = [];
      const inputHead: TableHead[] = [];

      notifyList.forEach((item) => {
        const {
          type,
          label,
          is_active: isActive,
          icon,
        } = item;

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

  watch(active, () => {
    panelList.value.forEach(item => Object.assign(item, { open: false }));
  });

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
    const totalMinutes = mergedIntervals.reduce((total, interval) => total + (interval.end - interval.start + 1), 0);

    return totalMinutes === 24 * 60;
  };

  const minutesToHoursAndMinutes = (minutes: number) => {
    const hour = Math.floor(minutes / 60);
    const minute = minutes % 60;
    const hoursStr = String(hour).padStart(2, '0');
    const minuteStr = String(minute).padStart(2, '0');

    return `${hoursStr}:${minuteStr}`;
  };

  const findFirstAvailableTimeSlot = () => {
    const timeRanges = panelList.value.map(item => item.timeRange);
    const fullDayInMinutes = 24 * 60;

    // 创建一个数组，用于表示整天的占用情况，初始都为空闲
    const availableMinutes = new Array(fullDayInMinutes).fill(true);

    // 根据给定的时间段将已占用的分钟设置为 false
    for (const timeRangeItem of timeRanges) {
      const {
        start,
        end,
      } = timeRangeFormatter(timeRangeItem);

      for (let i = start; i <= end; i++) {
        availableMinutes[i] = false;
      }
    }

    // 查找第一个可用时间段的开始和结束分钟数
    let firstAvailableStart = null;
    let firstAvailableEnd = null;

    for (let i = 0; i < fullDayInMinutes; i++) {
      if (availableMinutes[i]) {
        firstAvailableStart = i;
        while (i < fullDayInMinutes && availableMinutes[i]) {
          i += 1;
        }
        firstAvailableEnd = i - 1;
        break;
      }
    }

    if (firstAvailableStart && firstAvailableEnd) {
      return [
        minutesToHoursAndMinutes(firstAvailableStart),
        minutesToHoursAndMinutes(firstAvailableEnd),
      ];
    }

    return ['00:00', '23:59'];
  };

  const addPanel = () => {
    const name = Math.random()
      .toString(16)
      .substring(4, 10);

    panelList.value.push({
      name,
      open: false,
      timeRange: findFirstAvailableTimeSlot(),
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

    setTimeout(() => {
      active.value = name;
    });
  };

  const setInitPanelList = () => {
    const { type, details } = props;

    if (type === 'add') {
      addPanel();
    } else if (type === 'edit' || type === 'copy') {
      if (details?.alert_notice) {
        panelList.value = details.alert_notice.map((item) => {
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

        active.value = panelList.value[0].name;
      } else {
        addPanel();
      }
    }
  };

  const areTimeRangesOverlapping = () => {
    const minuteOccupied = new Array(24 * 60).fill(false); // 创建一个布尔数组，用于跟踪每分钟的占用情况
    const timeRanges = panelList.value.map(item => item.timeRange);

    for (const timeRangeItem of timeRanges) {
      const {
        start,
        end,
      } = timeRangeFormatter(timeRangeItem);

      // 检查时间段是否和已占用的时间冲突
      for (let i = start; i < end; i++) {
        if (minuteOccupied[i]) {
          return true; // 时间段重叠
        }
        minuteOccupied[i] = true;
      }
    }

    return false; // 时间段不重叠
  };

  const handleTimeChange = (date: string[], index: number) => {
    panelList.value[index].timeRange = date;
  };

  const setTimePickerRef = (el: TimePickerRef, index: number) => {
    if (el) {
      timePickerRefs[index] = el;
    }
  };

  const handleTabClick = (index: number) => {
    const item = panelList.value[index];

    if (item.name === active.value) {
      item.open = !item.open;
      currentPanelIndex = index;
      currentPanelTimeRange = _.cloneDeep(item.timeRange);

      nextTick(() => {
        timePickerRefs[index].pickerDropdownRef.forceUpdate();
      });
    }
  };

  const handleTabDelete = (index: number) => {
    panelList.value.splice(index, 1);

    nextTick(() => {
      // 默认值
      if (panelList.value.length === 0) {
        addPanel();
      }
    });
  };

  const timeArrayFormatter = (timeArr: string[]): string =>  {
    if (timeArr && timeArr.length === 2) {
      const [start, end] = timeArr;
      let startArr = start.split(':');
      let endArr = end.split(':');

      // 可能为HH:MM:DD或HH:MM，统一为HH:MM
      if (startArr.length > 2) {
        startArr = startArr.slice(0, 2);
      }
      if (endArr.length > 2) {
        endArr = endArr.slice(0, 2);
      }

      return `${startArr.join(':')} ~ ${endArr.join(':')}`;
    }

    return '';
  };

  const handleOpenMackClick = () => {
    const panelItem = panelList.value[currentPanelIndex];

    if (areTimeRangesOverlapping()) {
      messageWarn(t('时间段重叠了'));
      panelItem.timeRange = currentPanelTimeRange;
    }

    panelItem.open = false;
    currentPanelIndex = -1;
    currentPanelTimeRange = [];
  };

  defineExpose<Exposes>({
    getSubmitData() {
      const submitData = panelList.value.map((item) => {
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
      display: none;
      font-size: 18px;
    }

    :deep(.bk-tab-header-item) {
      min-height: 42px;

      &:hover {
        .tab-delete-btn {
          display: inherit;
        }
      }

      .add-panel-button {
        height: 100%;
      }
    }

    .tab-penel-box {
      padding: 0 24px 8px;
    }

    .notice-text {
      font-size: 12px;
      color: @gray-color;
    }

    .panel-item-table {
      width: 100%;
      overflow: auto;
      border: 1px solid #DCDEE5;
      border-bottom: none;
      border-radius: 2px;

      .table-row {
        display: flex;

        .table-row-item {
          display: flex;
          min-width: 120px;
          padding: 0 12px;
          border-bottom: 1px solid #DCDEE5;
          flex: 1;
          align-items: center;
          justify-content: center;
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

          .table-row-type-text {
            padding-left: 6px;
            font-size: 12px;
            line-height: 18px;
            border-radius: 1px;
          }

          .table-row-type-text-default {
            border-left: 4px solid @primary-color;
          }

          .table-row-type-text-warning {
            border-left: 4px solid @warning-color;
          }

          .table-row-type-text-error {
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

    .notice-mothod-open-mask {
      position: fixed;
      top: 0;
      left: 0;
      z-index: 1;
      width: 100%;
      height: 100%
    }
  }
</style>
