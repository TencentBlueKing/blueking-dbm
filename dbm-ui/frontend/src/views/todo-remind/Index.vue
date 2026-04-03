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
  <BkLoading :loading="getTodoRemindLoading || groupNotifyLoading">
    <SmartAction
      class="todo-remind-page"
      :offset-target="getSmartActionOffsetTarget">
      <BkCard
        :border="false"
        class="mb-32"
        :show-header="false">
        <BkAlert
          class="mt-16"
          :title="
            t(
              '提醒范围：自动涵盖个人工作台「我的待办」下所有待办类型（单据待办、告警事件待办、巡检待办、主机处理待办、集群下架待办、风险备忘录），未来新增待办类型自动纳入。',
            )
          " />
        <DbForm
          ref="form"
          class="notice-form"
          :label-width="100"
          :model="formData">
          <DbFormItem
            :label="t('启用提醒')"
            required>
            <BkSwitcher
              v-model="formData.isEnable"
              theme="primary" />
          </DbFormItem>
          <DbFormItem
            :label="t('提醒时间')"
            property="remindTime"
            required>
            <BkTimePicker
              v-model="formData.remindTime"
              append-to-body
              :disabled="!formData.isEnable"
              format="HH:mm"
              style="width: 120px" />
            <span class="time-text ml-8">{{ t('每日') }}</span>
          </DbFormItem>
          <DbFormItem
            :label="t('通知方式')"
            property="notice"
            required
            :rules="noticeRules">
            <BkTable
              align="center"
              border="full"
              class="notice-table"
              :columns="columns"
              :data="formData.notice"
              header-align="center">
            </BkTable>
          </DbFormItem>
        </DbForm>
      </BkCard>
      <template #action>
        <BkButton
          class="w-88"
          :disabled="resetTodoRemindLoading"
          :loading="updateTodoRemindLoading"
          theme="primary"
          @click="handleSave">
          {{ t('保存') }}
        </BkButton>
        <DbPopconfirm
          ref="dbPopconfirm"
          :confirm-handler="handleReset"
          :content="t('重置将会恢复默认设置的内容')"
          :title="t('确认重置')">
          <span>
            <BkButton
              action-id="biz_notify_config"
              class="ml-8 w-88"
              :disabled="updateTodoRemindLoading"
              :loading="resetTodoRemindLoading">
              {{ t('重置') }}
            </BkButton>
          </span>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAlarmGroupNotifyList } from '@services/source/monitorNoticeGroup';
  import { getTodoRemind, updateTodoRemind } from '@services/source/todoRemind';

  import { InputMessageTypes, MessageTipMap, MessageTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  type AlarmGroupNotify = ServiceReturnType<typeof getAlarmGroupNotifyList>;

  interface DataRow {
    checkbox: Record<string, boolean>;
    input: Record<string, string>;
  }

  const { t } = useI18n();

  const formRef = useTemplateRef('form');

  const formData = reactive({
    isEnable: false,
    notice: [] as DataRow[],
    remindTime: '10:00',
  });

  const DefaultMessageTypeList = [MessageTypes.RTX];
  const noticeRules = [
    {
      message: t('请至少启用一种通知渠道'),
      required: true,
      trigger: 'change',
      validator: (value: DataRow[]) => {
        const tableItem = value[0];
        return (
          Object.values(tableItem.checkbox).some((item) => item) || Object.values(tableItem.input).some((item) => item)
        );
      },
    },
  ];
  const columns = computed(() => {
    // input 类型的放最后
    const activeTypeMap = (alarmGroupNotifyList.value || []).reduce<{
      checkbox: AlarmGroupNotify;
      input: AlarmGroupNotify;
    }>(
      (prevMap, item) => {
        if ([MessageTypes.MAIL, MessageTypes.RTX, MessageTypes.WECOM_ROBOT].includes(item.type as MessageTypes)) {
          if (InputMessageTypes.includes(item.type)) {
            Object.assign(prevMap.input, prevMap.input.concat(item));
          } else {
            Object.assign(prevMap.checkbox, prevMap.checkbox.concat(item));
          }
        }
        return prevMap;
      },
      {
        checkbox: [],
        input: [],
      },
    );

    const nofityColumns = [...activeTypeMap.checkbox, ...activeTypeMap.input].map((item) => {
      const isInputType = InputMessageTypes.includes(item.type);
      const messageTip = MessageTipMap[item.type];
      return {
        field: item.type,
        minWidth: isInputType ? 320 : 120,
        render: ({ data }: { data: DataRow }) => {
          if (isInputType) {
            return (
              <bk-input
                v-model={data.input[item.type]}
                disabled={!formData.isEnable}
                placeholder={t('请输入群ID')}
              />
            );
          }
          return (
            <bk-checkbox
              v-model={data.checkbox[item.type]}
              disabled={!formData.isEnable}
            />
          );
        },
        renderHead: () => (
          <div class='message-type-head'>
            <img
              height='20'
              src={`data:image/png;base64,${item.icon}`}
              width='20'
            />
            <span class='ml-4'>{item.label}</span>
            {messageTip && (
              <db-icon
                v-bk-tooltips={{
                  content: messageTip,
                }}
                class='message-type-head-tip ml-4'
                type='attention'
              />
            )}
          </div>
        ),
        showOverflowTooltip: false,
      };
    });

    return nofityColumns;
  });

  const {
    data: todoRemindData,
    loading: getTodoRemindLoading,
    run: runGetTodoRemind,
  } = useRequest(getTodoRemind, {
    manual: true,
  });

  const {
    data: alarmGroupNotifyList,
    loading: groupNotifyLoading,
    run: runGetAlarmGroupNotifyList,
  } = useRequest(getAlarmGroupNotifyList, {
    manual: true,
  });

  const { loading: updateTodoRemindLoading, run: runUpdateTodoRemind } = useRequest(updateTodoRemind, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('保存成功'));
      window.changeConfirm = false;
      getData();
    },
  });

  const { loading: resetTodoRemindLoading, run: runResetTodoRemind } = useRequest(updateTodoRemind, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('重置成功'));
      window.changeConfirm = false;
      getData();
    },
  });

  watch([todoRemindData, alarmGroupNotifyList], () => {
    if (todoRemindData.value && alarmGroupNotifyList.value) {
      const activeTypeMap = alarmGroupNotifyList.value.reduce<{
        checkbox: Record<string, boolean>;
        input: Record<string, string>;
      }>(
        (prevMap, item) => {
          if (item.is_active) {
            if (InputMessageTypes.includes(item.type)) {
              Object.assign(prevMap.input, {
                [item.type]: '',
              });
            } else {
              Object.assign(prevMap.checkbox, {
                [item.type]: false,
              });
            }
          }
          return prevMap;
        },
        {
          checkbox: {},
          input: {},
        },
      );

      const initSetting = _.cloneDeep(activeTypeMap);
      const { is_enable: isEnable, notice, remind_time: remindTime } = todoRemindData.value;
      if (todoRemindData.value.notice.length === 0) {
        DefaultMessageTypeList.forEach((type) => {
          if (initSetting.checkbox[type] !== undefined) {
            initSetting.checkbox[type] = true;
          }
        });
      } else {
        const noticeSetting =
          notice.length > 0
            ? Object.fromEntries(notice.map((item) => [item.type, item.value]))
            : Object.fromEntries(DefaultMessageTypeList.map((defaultItem) => [defaultItem, '']));

        Object.keys(initSetting.checkbox).forEach((initSettingKey) => {
          initSetting.checkbox[initSettingKey] = noticeSetting[initSettingKey] === '' ? true : false;
        });
        Object.keys(initSetting.input).forEach((initSettingKey) => {
          initSetting.input[initSettingKey] = noticeSetting[initSettingKey] || '';
        });
      }

      Object.assign(formData, {
        isEnable: isEnable,
        notice: [
          {
            checkbox: initSetting.checkbox,
            input: initSetting.input,
          },
        ],
        remindTime: `${remindTime.hour}:${remindTime.minute}`,
      });
    }
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getData = () => {
    runGetTodoRemind();
    runGetAlarmGroupNotifyList({});
  };

  const handleSave = async () => {
    await formRef.value!.validate();

    const { isEnable, notice, remindTime } = formData;
    const [hour, minute] = remindTime.split(':');
    const { checkbox, input } = notice[0];
    const checkboxNotice = Object.entries(checkbox)
      .filter(([, value]) => value)
      .map(([type]) => ({
        type,
        value: '',
      }));
    const inputNotice = Object.entries(input)
      .filter(([, value]) => value)
      .map(([type, value]) => ({
        type,
        value,
      }));

    runUpdateTodoRemind({
      is_enable: isEnable,
      notice: [...checkboxNotice, ...inputNotice],
      remind_time: {
        hour,
        minute,
      },
    });
  };

  const handleReset = () => {
    runResetTodoRemind({
      is_enable: false,
      notice: DefaultMessageTypeList.map((type) => ({
        type,
        value: '',
      })),
      remind_time: {
        hour: '10',
        minute: '00',
      },
    });
  };

  // 初始化查询
  getData();
</script>

<style lang="less">
  .todo-remind-page {
    // padding: 20px;

    .db-card {
      & ~ .db-card {
        margin: 20px;
      }
    }

    .notice-form {
      padding: 24px 0;

      .bk-form-label {
        font-size: 12px;
      }

      .time-text {
        font-size: 12px;
        color: #979ba5;
      }

      .notice-table {
        th {
          &.common-head {
            font-weight: bolder;
          }

          .message-type-head {
            display: flex;
            align-items: center;
            justify-content: center;

            .message-type-head-tip {
              font-size: 14px;
              color: #63656e;
            }
          }
        }
      }
    }
  }
</style>
