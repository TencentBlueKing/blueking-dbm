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
      class="ticket-notice"
      :offset-target="getSmartActionOffsetTarget">
      <BkCard
        :border="false"
        class="mb-32"
        :show-header="false">
        <DbForm
          class="notice-form"
          :label-width="100">
          <DbFormItem
            :label="t('通知方式')"
            required>
            <BkTable
              align="center"
              border="full"
              class="notice-table"
              :columns="columns"
              :data="dataList"
              header-align="center"
              :header-cell-class-name="setHeadCellClassName">
            </BkTable>
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
        <DbPopconfirm
          ref="dbPopconfirm"
          :confirm-handler="handleReset"
          :content="t('重置将会恢复默认设置的内容')"
          :title="t('确认重置')">
          <AuthButton
            action-id="biz_notify_config"
            class="ml8 w-88"
            :disabled="updateSettingLoading"
            :loading="resetSettingLoading"
            :resource="bizId">
            {{ t('重置') }}
          </AuthButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TicketModel from '@services/model/ticket/ticket';
  import { getBizSettingList, updateBizSetting } from '@services/source/bizSetting';
  import { getAlarmGroupNotifyList } from '@services/source/monitorNoticeGroup';

  import { InputMessageTypes, MessageTipMap, MessageTypes } from '@common/const'

  import { messageSuccess } from '@utils';

  type AlarmGroupNotify = ServiceReturnType<typeof getAlarmGroupNotifyList>
  type TicketNoticeSetting = Record<string, Record<string, boolean | string[]>>

  interface DataRow {
    status: string;
    statusText: string;
    noticeMember: string[];
    checkbox: Record<string, boolean>,
    input: Record<string, string>,
  }

  const { t } = useI18n();

  const dataList = ref<DataRow[]>([]);

  const bizId = window.PROJECT_CONFIG.BIZ_ID
  const DefaultMessageTypeList = [MessageTypes.MAIL, MessageTypes.RTX]
  const NoticeTicketTypeList = Object.entries(TicketModel.statusTextMap).filter(([status]) => ![TicketModel.STATUS_RUNNING, TicketModel.STATUS_TIMER].includes(status))

  const columns = computed(() => {
    const baseColumns = [
      {
        label: t('单据状态'),
        field: 'statusText',
        width: 100,
      },
      {
        label: t('通知对象'),
        field: 'noticeMember',
        width: 200,
        render: ({ data } : { data: DataRow }) => data.noticeMember.join('，')
      },
    ];

    // input 类型的放最后
    const activeTypeMap = (alarmGroupNotifyList.value || []).reduce<{
      checkbox: AlarmGroupNotify,
      input: AlarmGroupNotify,
    }>((prevMap, item) => {
      if (item.is_active) {
        if (InputMessageTypes.includes(item.type)) {
          Object.assign(prevMap.input, prevMap.input.concat(item))
        } else {
          Object.assign(prevMap.checkbox, prevMap.checkbox.concat(item))
        }
      }
      return prevMap;
    }, {
      checkbox: [],
      input: []
    })

    const nofityColumns = [...activeTypeMap.checkbox, ...activeTypeMap.input].map(item => {
      const isInputType = InputMessageTypes.includes(item.type)
      const messageTip = MessageTipMap[item.type]
      return {
        field: item.type,
        minWidth: isInputType ? 320 : 120,
        showOverflowTooltip: false,
        renderHead: () => (
          <div class="message-type-head">
            <img
              height="20"
              src={`data:image/png;base64,${item.icon}`}
              width="20" />
            <span
              class="ml-4">
              { item.label }
            </span>
            {
              messageTip && (
                <db-icon
                  class="message-type-head-tip ml-4"
                  v-bk-tooltips={{
                    content: messageTip
                  }}
                  type="attention" />
              )
            }
          </div>
        ),
        render: ({ data } : { data: DataRow }) => {
          if (isInputType) {
            return (
              <bk-input
                v-model={data.input[item.type]}
                placeholder={t('请输入群ID')}/>
            )
          }
          return <bk-checkbox v-model={data.checkbox[item.type]}/>
        }
      }
    });

    return [...baseColumns, ...nofityColumns];
  });

  const { loading: getBizSettingLoading, data: bizSetting, run: runGetBizSettingList } = useRequest(getBizSettingList, {
    manual: true,
  });

  const { loading: groupNotifyLoading, data: alarmGroupNotifyList, run: runGetAlarmGroupNotifyList } = useRequest(getAlarmGroupNotifyList, {
    manual: true,
  });

  const { loading: updateSettingLoading, run: runUpdateBizSetting } = useRequest(updateBizSetting, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('保存成功'));
      getData()
    },
  });

  const { loading: resetSettingLoading, run: runResetBizSetting } = useRequest(updateBizSetting, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('重置成功'));
      getData()
    },
  });

  watch([bizSetting, alarmGroupNotifyList], () => {
    if (bizSetting.value && alarmGroupNotifyList.value) {
      const activeTypeMap = alarmGroupNotifyList.value.reduce<{
        checkbox: Record<string, boolean>,
        input: Record<string, string>,
      }>((prevMap, item) => {
        if (item.is_active) {
          if (InputMessageTypes.includes(item.type)) {
            Object.assign(prevMap.input, {
              [item.type]: ''
            })
          } else {
            Object.assign(prevMap.checkbox, {
              [item.type]: false
            })
          }
        }
        return prevMap;
      }, {
        checkbox: {},
        input: {}
      })

      const isBizSettingEmpty = _.isEmpty(bizSetting.value) ||  _.isEmpty(bizSetting.value.NOTIFY_CONFIG)
      const list: DataRow[] = []

      NoticeTicketTypeList.forEach(([status, statusText]) => {
        const initSetting = _.cloneDeep(activeTypeMap)
        if (isBizSettingEmpty) {
          DefaultMessageTypeList.forEach(type => {
            if (initSetting.checkbox[type] !== undefined) {
              initSetting.checkbox[type] = true;
            }
          });
        } else {
          const statusBizSetting = bizSetting.value!.NOTIFY_CONFIG[status]
          Object.keys(initSetting.checkbox).forEach(initSettingKey => {
            initSetting.checkbox[initSettingKey] = statusBizSetting[initSettingKey] || false
          })
          Object.keys(initSetting.input).forEach(initSettingKey => {
            initSetting.input[initSettingKey] = (statusBizSetting[initSettingKey] || []).join(',')
          })
        }

        list.push({
          status,
          statusText,
          noticeMember: status === TicketModel.STATUS_APPROVE ? [t('审批人')] : [t('提单人'), t('协助人')],
          checkbox: initSetting.checkbox,
          input: initSetting.input
        })
      })
      dataList.value = list
    }
  })

  const setHeadCellClassName = ({ columnIndex }: { columnIndex: number }) => columnIndex < 2 ? 'common-head' : ''

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getData = () => {
    runGetBizSettingList({
      bk_biz_id: bizId,
      key: 'NOTIFY_CONFIG',
    })
    runGetAlarmGroupNotifyList({
      bk_biz_id: bizId
    })
  }

  const handleSave = () => {
    runUpdateBizSetting({
      bk_biz_id: bizId,
      key: 'NOTIFY_CONFIG',
      value: dataList.value.reduce<TicketNoticeSetting>((prevMap, dataItem) => {
        const checkboxMap = Object.entries(dataItem.checkbox).reduce<Record<string, boolean>>((prevMap, [key, value])=> {
          if (value) {
            return Object.assign({}, prevMap, { [key]: value })
          }
          return prevMap
        }, {})
        const inputMap = Object.entries(dataItem.input).reduce<Record<string, string[]>>((prevMap, [key, value])=> {
          if (value) {
            return Object.assign({}, prevMap, { [key]: value.split(',') })
          }
          return prevMap
        }, {})
        return Object.assign({}, prevMap, {
          [dataItem.status]: {
            ...checkboxMap,
            ...inputMap
          }
        })
      }, {})
    })
  };

  const handleReset = () => {
    runResetBizSetting({
      bk_biz_id: bizId,
      key: 'NOTIFY_CONFIG',
      value: NoticeTicketTypeList.reduce<TicketNoticeSetting>((prevSettingMap, [status]) => Object.assign({}, prevSettingMap, {
        [status]: DefaultMessageTypeList.reduce<Record<string, boolean>>((prevValueMap, type) => Object.assign({}, prevValueMap, {
          [type]: true
        }), {})
      }), {})
    })
  };

  // 初始化查询
  getData()
</script>

<style lang="less" scoped>
  .ticket-notice {
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
    }

    :deep(.notice-table) {
      th {
        &.common-head {
          font-weight: bolder;
        }

        .message-type-head {
          display: flex;
          align-items: center;

          .message-type-head-tip {
            font-size: 14px;
            color: #63656e;
          }
        }
      }
    }
  }
</style>
