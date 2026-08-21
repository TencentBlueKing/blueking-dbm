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
              theme="primary"
              @change="handleEnableChange" />
          </DbFormItem>
          <DbFormItem
            :label="t('提醒时间')"
            property="remindTime"
            required>
            <div class="remind-time">
              <div class="time-text">{{ t('每日') }}</div>
              <BkTimePicker
                v-model="formData.remindTime"
                append-to-body
                class="time-picker"
                :disabled="!formData.isEnable"
                format="HH:mm"
                style="width: 120px" />
              <BkCheckbox
                v-model="formData.dayOfWeek"
                class="ml-8"
                :disabled="!formData.isEnable">
                {{ t('周末（周六/周日）不发送提醒') }}
              </BkCheckbox>
            </div>
          </DbFormItem>
          <DbFormItem
            :label="t('通知渠道')"
            property="notice"
            required
            :rules="noticeRules">
            <div class="channel-config">
              <!-- 个人通知（全员） -->
              <div class="channel-group">
                <div class="channel-group-head">
                  <span class="channel-group-title-text">{{ t('个人通知（全员）') }}</span>
                  <span class="channel-group-inline-desc">
                    {{ t('面向所有有待办的用户，按人发送个性化汇总；与是否启用群聊无关。') }}
                  </span>
                </div>
                <div class="personal-channels">
                  <BkCheckbox
                    v-for="item in personalChannelList"
                    :key="item.type"
                    v-model="formData.notice.checkbox[item.type]"
                    class="channel-check-label"
                    :disabled="!formData.isEnable"
                    @change="handleCheckboxChange">
                    <img
                      class="channel-icon"
                      :src="`data:image/png;base64,${item.icon}`" />
                    {{ item.label }}
                  </BkCheckbox>
                </div>
              </div>
              <!-- 企微群聊（仅 DBA） -->
              <div class="channel-group">
                <div class="channel-group-head">
                  <span class="channel-group-title-text">{{ t('企微群聊（仅 DBA）') }}</span>
                  <span class="channel-group-inline-desc">{{
                    t('仅汇总 DBA 待办并发送到所填群聊，不包含普通用户。')
                  }}</span>
                </div>
                <div class="group-channel-row mb-12">
                  <span class="group-field-label">{{ t('企微群聊 ID') }}</span>
                  <BkInput
                    v-model="formData.notice.input[MessageTypes.WECOM_ROBOT]"
                    class="group-input-wrap"
                    clearable
                    :disabled="!formData.isEnable"
                    :placeholder="t('请输入群聊 ID，多个用英文逗号分隔')" />
                  <DbIcon
                    v-bk-tooltips="{ content: t('填写企微群聊 ID，多个群 ID 用英文逗号分隔') }"
                    class="group-help-icon"
                    type="attention" />
                </div>
              </div>
            </div>
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
        <BkButton
          action-id="biz_notify_config"
          class="ml-8 w-88"
          :disabled="updateTodoRemindLoading"
          :loading="resetTodoRemindLoading"
          @click="handleReset">
          {{ t('恢复默认') }}
        </BkButton>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getAlarmGroupNotifyList } from '@services/source/monitorNoticeGroup';
  import { getTodoRemind, updateTodoRemind } from '@services/source/todoRemind';

  import { InputMessageTypes, MessageTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  const { t } = useI18n();

  const formRef = useTemplateRef('form');

  const formData = reactive({
    dayOfWeek: false,
    isEnable: false,
    notice: {
      checkbox: {} as Record<string, boolean>,
      input: {} as Record<string, string>,
    },
    remindTime: '10:00',
  });

  const DefaultMessageTypeList = [MessageTypes.RTX];

  // 个人通知渠道列表（checkbox类型）
  const personalChannelList = computed(() => {
    return (alarmGroupNotifyList.value || []).filter((item) =>
      [MessageTypes.MAIL, MessageTypes.RTX].includes(item.type as MessageTypes),
    );
  });

  const noticeRules = [
    {
      message: t('请至少启用一种通知渠道'),
      required: true,
      trigger: 'change',
      validator: () => {
        if (formData.isEnable) {
          const { checkbox, input } = formData.notice;
          return Object.values(checkbox).some((item) => item) || Object.values(input).some((item) => item);
        }
        return true;
      },
    },
  ];

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
      messageSuccess(t('恢复默认成功'));
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
        dayOfWeek: remindTime.day_of_week ? true : false,
        isEnable: isEnable,
        notice: {
          checkbox: initSetting.checkbox,
          input: initSetting.input,
        },
        remindTime: `${remindTime.hour}:${remindTime.minute}`,
      });
    }
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getData = () => {
    runGetTodoRemind();
    runGetAlarmGroupNotifyList({});
  };

  const handleEnableChange = () => {
    formRef.value!.validate('notice');
  };

  const handleCheckboxChange = () => {
    formRef.value!.validate('notice');
  };

  const handleSave = async () => {
    await formRef.value!.validate();

    const { dayOfWeek, isEnable, notice, remindTime } = formData;
    const [hour, minute] = remindTime.split(':');
    const { checkbox, input } = notice;
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
        day_of_week: dayOfWeek ? '1-5' : undefined,
        hour,
        minute,
      },
    });
  };

  const handleReset = () => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      content: t('当前页面的所有配置将恢复为系统默认值。'),
      onConfirm: () => {
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
      },
      title: t('确认恢复默认值？'),
      type: 'warning',
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

      .remind-time {
        display: flex;
        align-items: center;

        .time-text {
          height: 32px;
          padding: 0 8px;
          align-items: center;
          font-size: 12px;
          background-color: #fafbfd;
          border: 1px solid #c4c6cc;
          border-right: none;
          border-radius: 2px 0 0 2px;
        }

        .time-picker {
          .bk-date-picker-editor {
            border-radius: 0 2px 2px 0;
          }
        }
      }

      // 通知渠道配置样式
      .channel-config {
        width: 100%;
        max-width: 700px;
      }

      .channel-group {
        margin-top: 6px;

        &:not(:first-child) {
          padding-top: 20px;
          margin-top: 20px;
          border-top: 1px solid #f0f1f5;
        }
      }

      .channel-group-head {
        margin-bottom: 12px;
        font-size: 13px;
        line-height: 1.65;
        color: #313238;
      }

      .channel-group-title-text {
        font-weight: 600;
        color: #313238;
      }

      .channel-group-inline-desc {
        margin-left: 8px;
        font-size: 12px;
        font-weight: normal;
        color: #979ba5;
      }

      .personal-channels {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: 24px;
      }

      .channel-check-label {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        color: #313238;
        cursor: pointer;

        .bk-checkbox-label {
          display: flex;
          margin-left: 2px;
          align-items: center;
        }

        .channel-icon {
          width: 16px;
          height: 16px;
          flex-shrink: 0;
          margin-right: 4px;
        }
      }

      .group-channel-row {
        display: flex;
        align-items: center;
        gap: 10px;
        flex-wrap: wrap;
      }

      .group-field-label {
        font-size: 12px;
        color: #63656e;
        flex-shrink: 0;
      }

      .group-input-wrap {
        flex: 1;
        max-width: 480px;
        min-width: 200px;
      }

      .group-help-icon {
        font-size: 14px;
        color: #979ba5;
        flex-shrink: 0;
      }

      .bk-form-item.is-error .bk-input {
        border-color: #c4c6cc;
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
