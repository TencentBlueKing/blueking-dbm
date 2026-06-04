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
    ref="noticeMethodRef"
    class="notice-mothod"
    :label="t('通知方式')"
    property="method"
    required
    :rules="methodRules">
    <div>
      <p class="notice-text">
        {{ t('每个告警级别至少勾选一种渠道；勾选企微群聊时需填写群 ID（可按级别填不同群）') }}
      </p>
      <div
        v-for="(item, index) in panelList"
        :key="item.name"
        class="panel-item-table">
        <div class="table-row tabel-head-row">
          <div
            v-for="headItem in head"
            :key="headItem.label"
            class="table-row-item table-row-head-item"
            :class="{
              'table-row-type': !headItem.type,
              'table-row-checkbox': headItem.type && headItem.type !== MessageTypes.WXWORK_BOT,
              'table-row-input': headItem.type && headItem.type === MessageTypes.WXWORK_BOT,
            }">
            <DbIcon
              style="font-size: 16px"
              :type="headItem.icon" />
            <span
              class="ml-4"
              :class="{ 'label-bold': !headItem.type }">
              {{ headItem.label }}
            </span>
            <DbIcon
              v-if="headItem.tips"
              v-bk-tooltips="headItem.tips"
              class="message-type-head-tip ml-4"
              type="attention" />
          </div>
        </div>
        <div
          v-for="(dataItem, dataIndex) in item.dataList"
          :key="dataIndex"
          class="table-row table-content-row">
          <div class="table-row-item table-row-type">
            <div
              class="table-row-type-text"
              :class="[`table-row-type-text-${dataItem.type}`]">
              {{ dataItem.label }}
            </div>
          </div>
          <div
            v-for="(formDataItem, formDataIndex) in dataItem.formData"
            :key="formDataIndex"
            class="table-row-item table-row-checkbox"
            :class="{ 'table-row-input': formDataItem.type === MessageTypes.WXWORK_BOT }">
            <BkCheckbox
              v-model="formDataItem.checked"
              :disabled="disabled"
              @change="(value: boolean) => handleCheckChange(value, index, dataIndex, formDataIndex)" />
            <BkInput
              v-if="formDataItem.type === MessageTypes.WXWORK_BOT"
              v-model="formDataItem.input"
              class="ml-8"
              :disabled="disabled || !formDataItem.checked"
              :placeholder="formDataItem.checked ? t('请输入群 ID，多个 ID 以分号隔开') : t('不通知')" />
          </div>
        </div>
      </div>
    </div>
  </BkFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import NoticGroupModel from '@services/model/notice-group/notice-group';
  import { getAlarmGroupList } from '@services/source/monitorNoticeGroup';

  import { MessageTypes } from '@common/const';

  interface Props {
    details: AlarmGroupDetail;
    disabled: boolean;
    type: 'add' | 'edit' | 'copy' | '';
  }

  interface Exposes {
    getSubmitData: () => {
      alertNotice: AlarmGroupNotice[];
      channels: string[];
    };
  }

  type AlarmGroupDetail = ServiceReturnType<typeof getAlarmGroupList>['results'][number]['details'];
  type AlarmGroupNotice = AlarmGroupDetail['alert_notice'][number];

  interface LevelMapItem {
    label: string;
    level: 3 | 2 | 1;
    type: 'default' | 'warning' | 'error';
  }

  interface TableHead {
    icon: string;
    label: string;
    tips?: string;
    type: string;
  }

  const props = defineProps<Props>();
  const isReceiversSelectorShow = defineModel<boolean>('isReceiversSelectorShow', {
    required: true,
  });

  const { t } = useI18n();

  const wxworkBotItem = NoticGroupModel.NoticeMethodList.find((item) => item.type === MessageTypes.WXWORK_BOT)!;
  let head: TableHead[] = [
    {
      icon: '',
      label: t('告警级别'),
      type: '',
    },
    ...NoticGroupModel.NoticeMethodList.filter((item) => item.type !== MessageTypes.WXWORK_BOT),
    {
      ...wxworkBotItem,
      tips: [
        t('获取会话ID方法:'),
        t('1. 群聊列表右上角...面板，点击消息推送，搜索：蓝鲸监控(上云) 并添加进群'),
        t('2. 手动蓝鲸监控(上云)'),
        t('3. 复制会话ID粘贴到输入框，多个ID使用逗号分隔'),
      ].join('\n'),
    },
  ];

  const levelMap: Record<number, LevelMapItem> = {
    1: {
      label: t('致命'),
      level: 1,
      type: 'error',
    },
    2: {
      label: t('预警'),
      level: 2,
      type: 'warning',
    },
    3: {
      label: t('提醒'),
      level: 3,
      type: 'default',
    },
  };

  const panelInitData: {
    checked: boolean;
    input: string;
    type: string;
  }[] = [
    {
      checked: false,
      input: '',
      type: MessageTypes.MAIL,
    },
    {
      checked: false,
      input: '',
      type: MessageTypes.VOICE,
    },
    {
      checked: false,
      input: '',
      type: MessageTypes.RTX,
    },
    {
      checked: false,
      input: '',
      type: MessageTypes.WXWORK_BOT,
    },
  ];

  const methodRules = [
    {
      required: true,
      validator: () => {
        // 每个告警级别至少勾选一种渠道（含企微群聊）
        // 勾选企微群聊时必填群 ID
        for (const panelItem of panelList.value) {
          for (const dataItem of panelItem.dataList) {
            if (dataItem.formData.every((formDataItem) => !formDataItem.checked)) {
              return t('level 级别请至少配置一种通知方式', { level: levelMap[dataItem.level].label });
            }
            for (const formDataItem of dataItem.formData) {
              if (formDataItem.type === MessageTypes.WXWORK_BOT && formDataItem.checked && formDataItem.input === '') {
                return t('level 级别请输入企微群 ID', { level: levelMap[dataItem.level].label });
              }
            }
          }
        }

        return true;
      },
    },
  ];

  const noticeMethodRef = useTemplateRef('noticeMethodRef');

  const active = ref('');
  const panelList = ref<
    {
      dataList: ({
        formData: typeof panelInitData;
      } & LevelMapItem)[];
      name: string;
      open: boolean;
      timeRange: [string, string];
    }[]
  >([]);

  watch(active, () => {
    panelList.value.forEach((item) => Object.assign(item, { open: false }));
  });

  watch(
    panelList,
    () => {
      isReceiversSelectorShow.value = panelList.value.some((panelItem) =>
        panelItem.dataList.some((dataItem) =>
          dataItem.formData.some(
            (checkItem) =>
              [MessageTypes.MAIL, MessageTypes.RTX, MessageTypes.VOICE].includes(checkItem.type as MessageTypes) &&
              checkItem.checked,
          ),
        ),
      );
      noticeMethodRef.value?.validate();
    },
    { deep: true, immediate: true },
  );

  const addPanel = () => {
    const name = Math.random().toString(16).substring(4, 10);

    panelList.value.push({
      dataList: [
        {
          ...levelMap[3],
          formData: _.cloneDeep(panelInitData),
        },
        {
          ...levelMap[2],
          formData: _.cloneDeep(panelInitData),
        },
        {
          ...levelMap[1],
          formData: _.cloneDeep(panelInitData),
        },
      ],
      name,
      open: false,
      timeRange: ['00:00', '23:59'],
    });

    setTimeout(() => {
      active.value = name;
    });
  };

  const setInitPanelList = () => {
    const { details, type } = props;

    if (type === 'add') {
      addPanel();
    } else if (type === 'edit' || type === 'copy') {
      if (details.alert_notice) {
        panelList.value = details.alert_notice.map((item) => {
          const name = Math.random().toString(16).substring(4, 10);

          const dataList = item.notify_config.map((configItem) => {
            const formData = _.cloneDeep(panelInitData);

            configItem.notice_ways.forEach((wayItem) => {
              // 转为消息类型对应值
              const conversionType = wayItem.name;
              if ([MessageTypes.WXWORK_BOT].includes(conversionType as MessageTypes)) {
                const idx = formData.findIndex((inputItem) => inputItem.type === conversionType);

                if (idx > -1) {
                  formData[idx].input = (wayItem.receivers || []).join(',');
                  formData[idx].checked = true;
                }
              } else {
                const idx = formData.findIndex((checkboxItem) => checkboxItem.type === conversionType);

                if (idx > -1) {
                  formData[idx].checked = true;
                }
              }
            });

            return {
              ...levelMap[configItem.level],
              formData,
            };
          });

          return {
            dataList,
            name,
            open: false,
            timeRange: item.time_range.split('--') as [string, string],
          };
        });

        active.value = panelList.value[0].name;
      } else {
        addPanel();
      }
    }
  };
  setInitPanelList();

  const handleCheckChange = (value: boolean, index: number, dataIndex: number, formDataIndex: number) => {
    const formDataItem = panelList.value[index].dataList[dataIndex].formData[formDataIndex];
    if (formDataItem.type === MessageTypes.WXWORK_BOT && !value) {
      formDataItem.input = '';
      panelList.value[dataIndex].dataList[formDataIndex].formData.splice(formDataIndex, 1, formDataItem);
    }
  };

  defineExpose<Exposes>({
    getSubmitData() {
      let isUserTypeExist = false;
      let isRobotTypeExist = false;
      const submitData = panelList.value.map((item) => {
        const { dataList, timeRange } = item;

        return {
          notify_config: dataList.map((dataItem) => {
            const { formData, level } = dataItem;

            const noticeWaysCheck = formData.reduce(
              (prev, current) => {
                if (current.checked) {
                  const item = {
                    name: current.type,
                  };
                  if (current.type === MessageTypes.WXWORK_BOT) {
                    Object.assign(item, { receivers: current.input.split(',') });
                    isRobotTypeExist = true;
                  } else {
                    isUserTypeExist = true;
                  }
                  prev.push(item);
                }
                return prev;
              },
              [] as {
                name: string;
                receivers?: string[];
              }[],
            );

            return {
              level,
              notice_ways: noticeWaysCheck,
            };
          }),
          time_range: timeRange.join('--'),
        };
      });

      return {
        alertNotice: submitData,
        channels: [isUserTypeExist ? 'user' : '', isRobotTypeExist ? 'wxwork-bot' : ''].filter((item) => item),
      };
    },
  });
</script>

<style lang="less" scoped>
  .bk-form-item.is-error .bk-input {
    border-color: #c4c6cc;
  }

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
      border: 1px solid #dcdee5;
      border-bottom: none;
      border-radius: 2px;

      .table-row {
        display: flex;

        .table-row-item {
          display: flex;
          // width: 110px;
          padding: 0 12px;
          border-bottom: 1px solid #dcdee5;
          align-items: center;
          justify-content: center;
          flex-shrink: 0;

          &:not(:last-child) {
            border-right: 1px solid #dcdee5;
          }
        }

        .table-row-head-item {
          background-color: #fafbfd;
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

        .table-row-checkbox {
          min-width: 120px;
          // flex: 1;
        }

        .table-row-input {
          flex: 5;
        }

        .table-row-icon {
          font-size: 16px;
        }

        .label-bold {
          font-weight: bold;
        }

        .message-type-head-tip {
          font-size: 14px;
          color: #63656e;
          cursor: pointer;
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
      height: 100%;
    }
  }
</style>
