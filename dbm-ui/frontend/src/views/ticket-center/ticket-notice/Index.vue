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
  <BkLoading :loading="getBizSettingLoading || groupNotifyLoading">
    <SmartAction
      class="ticket-notice-page"
      :offset-target="getSmartActionOffsetTarget">
      <BkCard
        :border="false"
        class="mb-32"
        :show-header="false">
        <DbForm
          class="notice-form"
          form-type="vertical"
          :label-width="100">
          <DbFormItem>
            <template #label>
              <span class="main-label">{{ t('单据变更通知') }}</span>
              <span class="sub-label ml-4">（{{ t('单据状态发生变更时发送的通知') }}）</span>
            </template>
            <PrimaryTable
              bordered
              class="notice-table"
              :columns="changeColumns"
              :data="changeDataList"
              row-key="status">
            </PrimaryTable>
          </DbFormItem>
          <DbFormItem>
            <template #label>
              <span class="main-label">{{ t('单据执行通知') }}</span>
              <span class="sub-label ml-4">（{{ t('单据执行期间检测到异常而触发的通知') }}）</span>
            </template>
            <PrimaryTable
              bordered
              class="notice-table"
              :columns="excuteColumns"
              :data="excuteDataList"
              row-key="status">
            </PrimaryTable>
          </DbFormItem>
        </DbForm>
      </BkCard>
      <template #action>
        <AuthButton
          action-id="biz_notify_config"
          class="w-88"
          :disabled="resetSettingLoading"
          :loading="updateSettingLoading"
          :resource="bizId"
          theme="primary"
          @click="handleSave">
          {{ t('保存') }}
        </AuthButton>
        <AuthButton
          action-id="biz_notify_config"
          class="ml-8 w-88"
          :disabled="updateSettingLoading"
          :loading="resetSettingLoading"
          :resource="bizId"
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
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import { getBizSettingList, updateBizSetting } from '@services/source/bizSetting';
  import { getAlarmGroupNotifyList } from '@services/source/monitorNoticeGroup';

  import { BizSettingKeys, InputMessageTypes, MessageTipMap, MessageTypes } from '@common/const';

  import { messageSuccess } from '@utils';

  type AlarmGroupNotify = ServiceReturnType<typeof getAlarmGroupNotifyList>;
  type TicketNoticeSetting = Record<string, Record<string, boolean | string[]>>;

  interface DataRow {
    checkbox: Record<string, boolean>;
    input: Record<string, string>;
    noticeMember: string[];
    status: string;
    statusText: string;
  }

  const { t } = useI18n();

  const changeDataList = ref<DataRow[]>([]);
  const excuteDataList = ref<DataRow[]>([]);

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const DefaultMessageTypeList = [MessageTypes.RTX];
  const NoticeTicketTypeList = Object.entries(TicketModel.statusTextMap).filter(
    ([status]) => ![TicketModel.STATUS_RUNNING, TicketModel.STATUS_TIMER].includes(status),
  );

  const AI_TASK_GUARDIAN = 'AI_TASK_GUARDIAN';
  const TicketExcuteMap = {
    [AI_TASK_GUARDIAN]: t('集群产生告警'),
  };
  const TicketExcuteList = Object.entries(TicketExcuteMap);

  const getColumns = (statusTextLabel: string) => {
    const baseColumns: PrimaryTableCol[] = [
      {
        align: 'center',
        colKey: 'statusText',
        title: statusTextLabel,
        width: 100,
      },
      {
        align: 'center',
        cell: (_, { row }) => row.noticeMember.join('，'),
        colKey: 'noticeMember',
        title: t('通知对象'),
        width: 200,
      },
    ];

    // input 类型的放最后
    const activeTypeMap = (alarmGroupNotifyList.value || []).reduce<{
      checkbox: AlarmGroupNotify;
      input: AlarmGroupNotify;
    }>(
      (prevMap, item) => {
        if (item.is_active) {
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

    const nofityColumns = [...activeTypeMap.checkbox, ...activeTypeMap.input].map((item): PrimaryTableCol => {
      const isInputType = InputMessageTypes.includes(item.type);
      const messageTip = MessageTipMap[item.type];
      return {
        align: 'center',
        cell: (_, { row }) => {
          if (isInputType) {
            return (
              <bk-input
                v-model={row.input[item.type]}
                placeholder={t('请输入群ID')}
              />
            );
          }
          return <bk-checkbox v-model={row.checkbox[item.type]} />;
        },
        colKey: item.type,
        minWidth: isInputType ? 320 : 120,
        title: () => (
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
      };
    });

    return [...baseColumns, ...nofityColumns];
  };

  const changeColumns = computed(() => getColumns(t('单据状态')));
  const excuteColumns = computed(() => getColumns(t('通知场景')));

  const {
    data: bizSetting,
    loading: getBizSettingLoading,
    run: runGetBizSettingList,
  } = useRequest(getBizSettingList, {
    manual: true,
  });

  const {
    data: alarmGroupNotifyList,
    loading: groupNotifyLoading,
    run: runGetAlarmGroupNotifyList,
  } = useRequest(getAlarmGroupNotifyList, {
    manual: true,
  });

  const { loading: updateSettingLoading, run: runUpdateBizSetting } = useRequest(updateBizSetting, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('保存成功'));
      getData();
    },
  });

  const { loading: resetSettingLoading, run: runResetBizSetting } = useRequest(updateBizSetting, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('恢复默认成功'));
      getData();
    },
  });

  watch([bizSetting, alarmGroupNotifyList], () => {
    if (bizSetting.value && alarmGroupNotifyList.value) {
      changeDataList.value = getFormatList(NoticeTicketTypeList);
      excuteDataList.value = getFormatList(TicketExcuteList);
    }
  });

  const getFormatList = (settingList: string[][]) => {
    const activeTypeMap = alarmGroupNotifyList.value!.reduce<{
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

    const isBizSettingEmpty = _.isEmpty(bizSetting.value) || _.isEmpty(bizSetting.value[BizSettingKeys.NOTIFY_CONFIG]);
    const list: DataRow[] = [];

    settingList.forEach(([status, statusText]) => {
      const initSetting = _.cloneDeep(activeTypeMap);
      if (!isBizSettingEmpty && !_.isEmpty(bizSetting.value![BizSettingKeys.NOTIFY_CONFIG][status])) {
        // 若有新增状态，且存量设置不包含此状态，设初始值
        const statusBizSetting = bizSetting.value![BizSettingKeys.NOTIFY_CONFIG][status] || {};

        Object.keys(initSetting.checkbox).forEach((initSettingKey) => {
          initSetting.checkbox[initSettingKey] = statusBizSetting[initSettingKey] || false;
        });
        Object.keys(initSetting.input).forEach((initSettingKey) => {
          initSetting.input[initSettingKey] = (statusBizSetting[initSettingKey] || []).join(',');
        });
      }

      list.push({
        checkbox: initSetting.checkbox,
        input: initSetting.input,
        noticeMember: status === TicketModel.STATUS_APPROVE ? [t('审批人')] : [t('提单人'), t('协助人')],
        status,
        statusText,
      });
    });

    return list;
  };

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getData = () => {
    runGetBizSettingList({
      bk_biz_id: bizId,
      key: BizSettingKeys.NOTIFY_CONFIG,
    });
    runGetAlarmGroupNotifyList({
      bk_biz_id: bizId,
    });
  };

  const handleSave = () => {
    runUpdateBizSetting({
      bk_biz_id: bizId,
      key: BizSettingKeys.NOTIFY_CONFIG,
      value: [...changeDataList.value, ...excuteDataList.value].reduce<TicketNoticeSetting>((prevMap, dataItem) => {
        const checkboxMap = Object.entries(dataItem.checkbox).reduce<Record<string, boolean>>(
          (prevMap, [key, value]) => {
            if (value) {
              return Object.assign({}, prevMap, { [key]: value });
            }
            return prevMap;
          },
          {},
        );
        const inputMap = Object.entries(dataItem.input).reduce<Record<string, string[]>>((prevMap, [key, value]) => {
          if (value) {
            return Object.assign({}, prevMap, { [key]: value.split(',') });
          }
          return prevMap;
        }, {});
        return Object.assign({}, prevMap, {
          [dataItem.status]: {
            ...checkboxMap,
            ...inputMap,
          },
        });
      }, {}),
    });
  };

  const handleReset = () => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      content: t('当前页面的所有配置将恢复为系统默认值。'),
      onConfirm: () => {
        runResetBizSetting({
          bk_biz_id: bizId,
          key: BizSettingKeys.NOTIFY_CONFIG,
          value: [...NoticeTicketTypeList, ...TicketExcuteList].reduce<TicketNoticeSetting>(
            (prevSettingMap, [status]) =>
              Object.assign({}, prevSettingMap, {
                [status]: DefaultMessageTypeList.reduce<Record<string, boolean>>(
                  (prevValueMap, type) =>
                    Object.assign({}, prevValueMap, {
                      [type]: true,
                    }),
                  {},
                ),
              }),
            {},
          ),
        });
      },
      title: t('确认恢复默认值？'),
    });
  };

  // 初始化查询
  getData();
</script>

<style lang="less" scoped>
  .ticket-notice-page {
    padding: 20px;

    .db-card {
      & ~ .db-card {
        margin: 20px;
      }
    }

    :deep(.notice-form) {
      padding: 24px 0;

      .bk-form-label {
        font-size: 12px;
      }

      .main-label {
        font-size: 14px;
        font-weight: bolder;
        color: #313238;
      }

      .sub-label {
        color: #979ba5;
      }
    }

    :deep(.notice-table) {
      th {
        &:nth-child(-n + 2) {
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
</style>
