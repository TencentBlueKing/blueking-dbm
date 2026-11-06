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
          :label-width="140"
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
            :description="t('面向所有有待办的用户，按人发送个性化汇总；与是否启用群聊无关')"
            :label="t('个人通知渠道')"
            property="notice"
            :rules="noticeRules">
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
          </DbFormItem>
          <DbFormItem
            :description="t('仅汇总 DBA 待办并发送到所填群聊，不包含普通用户')"
            :label="t('企微群通知')">
            <div class="rule-toolbar mb-12">
              <BkButton
                class="w-88"
                :disabled="!formData.isEnable"
                @click="handleAddRule">
                <DbIcon
                  class="mr-4"
                  type="add" />
                {{ t('添加') }}
              </BkButton>
              <span
                v-if="formData.rules.length > 0"
                class="rule-summary">
                {{ t('共 {n} 条规则', { n: formData.rules.length }) }}
              </span>
            </div>
            <PrimaryTable
              v-if="formData.rules.length > 0"
              class="rule-table"
              :data="formData.rules"
              row-key="uid">
              <TableColumn
                col-key="chat_id"
                :min-width="220">
                <template #title>
                  <span class="rule-required">*</span>
                  {{ t('企微群 ID') }}
                </template>
                <template #default="{ row, rowIndex }: { row: IRuleRow; rowIndex: number }">
                  <DbFormItem
                    error-display-type="tooltips"
                    :property="`rules.${rowIndex}.chat_id`"
                    :rules="chatIdRules">
                    <BkInput
                      v-model="row.chat_id"
                      clearable
                      :disabled="!formData.isEnable"
                      :placeholder="t('请输入企微群 ID')" />
                  </DbFormItem>
                </template>
              </TableColumn>
              <TableColumn
                col-key="components"
                :min-width="280">
                <template #title>
                  <span class="rule-required">*</span>
                  {{ t('待办人员范围') }}
                </template>
                <template #default="{ row, rowIndex }: { row: IRuleRow; rowIndex: number }">
                  <DbFormItem
                    error-display-type="tooltips"
                    :property="`rules.${rowIndex}.components`"
                    :rules="componentRules">
                    <DbSelect
                      v-model="row.components"
                      class="rule-component-select"
                      clearable
                      collapse-tags
                      :disabled="!formData.isEnable"
                      :list="ruleComponentOptions"
                      multiple
                      multiple-mode="tag"
                      :placeholder="t('请选择组件')" />
                  </DbFormItem>
                </template>
              </TableColumn>
              <TableColumn
                col-key="row-operation"
                :title="t('操作')"
                :width="80">
                <template #default="{ rowIndex }: { rowIndex: number }">
                  <BkButton
                    :disabled="!formData.isEnable"
                    text
                    theme="danger"
                    @click="() => handleDeleteRule(rowIndex)">
                    {{ t('删除') }}
                  </BkButton>
                </template>
              </TableColumn>
            </PrimaryTable>
          </DbFormItem>
        </DbForm>
      </BkCard>
      <template #action>
        <AuthButton
          action-id="platform_todo_remind_manage"
          class="w-88"
          :disabled="resetTodoRemindLoading"
          :loading="updateTodoRemindLoading"
          theme="primary"
          @click="handleSave">
          {{ t('保存') }}
        </AuthButton>
        <AuthButton
          action-id="platform_todo_remind_manage"
          class="ml-8 w-88"
          :disabled="updateTodoRemindLoading"
          :loading="resetTodoRemindLoading"
          @click="handleReset">
          {{ t('恢复默认') }}
        </AuthButton>
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

  import { DBTypeInfos, DBTypes, MessageTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  const { t } = useI18n();

  const formRef = useTemplateRef('form');

  // 群通知规则行（uid 仅用于 PrimaryTable row-key，提交时剔除）
  interface IRuleRow {
    chat_id: string;
    components: DBTypes[];
    uid: string;
  }

  let uidSeed = 0;
  const createRuleRow = () => ({
    chat_id: '',
    components: [] as DBTypes[],
    uid: `rule_${++uidSeed}`,
  });

  const formData = reactive({
    dayOfWeek: false,
    isEnable: false,
    notice: {
      checkbox: {} as Record<string, boolean>,
    },
    remindTime: '10:00',
    rules: [] as IRuleRow[],
  });

  const DefaultMessageTypeList = [MessageTypes.RTX];

  // 待办人员范围可选组件（全部 DBTypes）
  const ruleComponentOptions = Object.values(DBTypes).map((id) => ({
    label: DBTypeInfos[id].name,
    value: id,
  }));

  // 个人通知渠道列表（checkbox类型）
  const personalChannelList = computed(() => {
    return (alarmGroupNotifyList.value || []).filter((item) =>
      [MessageTypes.MAIL, MessageTypes.RTX].includes(item.type as MessageTypes),
    );
  });

  const chatIdRules = [
    {
      message: t('不能为空'),
      required: true,
      trigger: 'change',
    },
    {
      message: t('企微群 ID 已存在'),
      trigger: 'change',
      validator: (value: string) => {
        if (!value.trim()) {
          return true;
        }
        // 跨规则查重，重复时命中行全部标错
        return formData.rules.filter((item) => item.chat_id.trim() === value.trim()).length <= 1;
      },
    },
  ];
  const componentRules = [
    {
      message: t('请选择待办人员范围'),
      required: true,
      trigger: 'change',
      validator: (value: DBTypes[]) => value.length > 0,
    },
  ];

  const noticeRules = [
    {
      message: t('请至少启用一种通知渠道'),
      required: true,
      trigger: 'change',
      validator: () => {
        if (formData.isEnable) {
          return Object.values(formData.notice.checkbox).some((item) => item);
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
      // 个人渠道仅 mail / rtx，历史遗留的 wecom_robot 项忽略
      const initSetting = _.cloneDeep(
        Object.fromEntries(
          alarmGroupNotifyList.value
            .filter(
              (item) => item.is_active && [MessageTypes.MAIL, MessageTypes.RTX].includes(item.type as MessageTypes),
            )
            .map((item) => [item.type, false]),
        ) as Record<string, boolean>,
      );

      const {
        is_enable: isEnable,
        notice,
        remind_time: remindTime,
        wecom_group_rules: wecomGroupRules,
      } = todoRemindData.value;
      if (notice.length === 0) {
        DefaultMessageTypeList.forEach((type) => {
          if (initSetting[type] !== undefined) {
            initSetting[type] = true;
          }
        });
      } else {
        const noticeSetting = Object.fromEntries(notice.map((item) => [item.type, item.value]));

        Object.keys(initSetting).forEach((initSettingKey) => {
          initSetting[initSettingKey] = noticeSetting[initSettingKey] === '' ? true : false;
        });
      }

      Object.assign(formData, {
        dayOfWeek: remindTime.day_of_week ? true : false,
        isEnable: isEnable,
        notice: {
          checkbox: initSetting,
        },
        remindTime: `${remindTime.hour}:${remindTime.minute}`,
        rules: (wecomGroupRules || []).map((item) => ({
          chat_id: item.chat_id,
          components: [...item.components] as DBTypes[],
          uid: `rule_${++uidSeed}`,
        })),
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

  // 群 ID 变化后延迟刷新跨行查重的错误态（空行跳过，避免误标必填错），防抖避免逐键触发全表校验
  const refreshChatIdValidate = _.debounce(() => {
    formData.rules.forEach((row, index) => {
      if (row.chat_id.trim()) {
        formRef.value?.validate(`rules.${index}.chat_id`);
      }
    });
  }, 300);

  watch(
    () => formData.rules.map((row) => row.chat_id),
    () => {
      refreshChatIdValidate();
    },
  );

  const handleAddRule = () => {
    formData.rules.push(createRuleRow());
  };

  const handleDeleteRule = (rowIndex: number) => {
    formData.rules.splice(rowIndex, 1);
  };

  const handleSave = async () => {
    await formRef.value!.validate();

    const { dayOfWeek, isEnable, notice, remindTime, rules } = formData;
    const [hour, minute] = remindTime.split(':');
    const checkboxNotice = Object.entries(notice.checkbox)
      .filter(([, value]) => value)
      .map(([type]) => ({
        type,
        value: '',
      }));

    runUpdateTodoRemind({
      is_enable: isEnable,
      notice: checkboxNotice,
      remind_time: {
        day_of_week: dayOfWeek ? '1-5' : undefined,
        hour,
        minute,
      },
      // 空数组即不发群消息
      wecom_group_rules: rules.map(({ chat_id: chatId, components }) => ({
        chat_id: chatId.trim(),
        components,
      })),
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
          wecom_group_rules: [],
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
      .channel-desc {
        font-size: 12px;
        line-height: 20px;
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

      .rule-toolbar {
        display: flex;
        align-items: center;
        gap: 12px;
      }

      .rule-summary {
        font-size: 12px;
        color: #979ba5;
      }

      .rule-required {
        margin-right: 4px;
        color: #ea3636;
      }

      .rule-table {
        .rule-component-select {
          width: 100%;
        }
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
