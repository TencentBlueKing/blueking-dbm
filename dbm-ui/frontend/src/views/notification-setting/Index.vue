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
  <div class="notification-setting-box">
    <div class="switch-box">
      <div class="title">
        {{ t('排班表发送') }}
      </div>
      <BkSwitcher
        v-model="formData.schedule_table.enable"
        size="small"
        theme="primary" />
    </div>
    <template v-if="formData.schedule_table.enable">
      <div class="item-box">
        <div class="title">
          {{ t('发送时间') }}
        </div>
        <div class="content">
          <BkSelect
            v-model="formData.schedule_table.send_at.freq"
            :clearable="false"
            style="width:86px">
            <BkOption
              v-for="(item, index) in dateList"
              :key="index"
              :label="item.label"
              :value="item.value" />
          </BkSelect>
          <BkSelect
            v-if="formData.schedule_table.send_at.freq === 'w'"
            v-model="formData.schedule_table.send_at.freq_values"
            :clearable="false"
            multiple
            style="width:180px">
            <BkOption
              v-for="(item, index) in weekdayList"
              :key="index"
              :label="item.label"
              :value="item.value" />
          </BkSelect>
          <SingleMonthDateRange
            v-else
            @change="handleSingleMonthDateRangeChange" />
          <BkTimePicker
            v-model="formData.schedule_table.send_at.time"
            class="time-pick"
            :clearable="false" />
        </div>
      </div>
      <div class="item-box">
        <div class="title">
          {{ t('发送内容') }}
        </div>
        <div class="content">
          <BkInput
            v-model="formData.schedule_table.send_day"
            :clearable="false"
            :max="100"
            :min="1"
            style="width:135px"
            type="number">
            <template #prefix>
              <div class="prefix-box">
                {{ t('近') }}
              </div>
            </template>
          </BkInput>
          <span>{{ t('天的排班结果') }}</span>
        </div>
      </div>
      <div class="item-box mb-24">
        <div class="title">
          {{ t('企业微信群 ID') }}
        </div>
        <div class="content">
          <BkInput
            v-model="formData.schedule_table.qywx_id"
            style="width:300px" />
          <!-- <DbIcon
            class="icon"
            type="attention-fill" /> -->
        </div>
      </div>
    </template>
    <div class="switch-box">
      <div class="title">
        {{ t('个人轮值通知') }}
      </div>
      <BkSwitcher
        v-model="formData.person_duty.enable"
        size="small"
        theme="primary" />
    </div>
    <template v-if="formData.person_duty.enable">
      <div class="item-box">
        <div class="title">
          {{ t('值班开始前') }}
        </div>
        <div class="content">
          <BkInput
            v-model="formData.person_duty.send_at.num"
            :clearable="false"
            :max="14"
            :min="1"
            style="width: 178px;"
            type="number">
            <template #suffix>
              <div class="suffix-box">
                <BkSelect
                  v-model="formData.person_duty.send_at.unit"
                  :clearable="false"
                  style="width:58px">
                  <BkOption
                    v-for="(item, index) in periodList"
                    :key="index"
                    :label="item.label"
                    :value="item.value" />
                </BkSelect>
              </div>
            </template>
          </BkInput>
          <span>{{ t('收到通知') }}</span>
        </div>
      </div>
    </template>
  </div>
  <div class="notification-setting-footer">
    <BkButton
      class="mr-8"
      theme="primary"
      @click="handleSubmit">
      {{ t('保存') }}
    </BkButton>
    <DbPopconfirm
      :confirm-handler="handleReset"
      :content="t('重置将会恢复默认设置的内容！')"
      :title="t('确认重置当前配置？')">
      <BkButton>
        {{ t('重置') }}
      </BkButton>
    </DbPopconfirm>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    getDutyNoticeConfig,
    updateDutyNoticeConfig,
  } from '@services/monitor';

  import {
    messageError,
    messageSuccess,
  } from '@utils';

  import SingleMonthDateRange from './components/SingleMonthDateRange.vue';

  type DutyConfig = ServiceReturnType<typeof getDutyNoticeConfig>

  function initData(data?: DutyConfig) {
    if (!data) {
      return ({
        person_duty: {
          enable: false,
          send_at: {
            num: 1,
            unit: 'h',
          },
        },
        schedule_table: {
          enable: false,
          qywx_id: '',
          send_at: {
            freq: 'w',
            time: '00:00:00',
            freq_values: [] as number[],
          },
          send_day: 7,
        },
      });
    }
    return data;
  }

  const { t } = useI18n();

  const formData = ref(initData());

  useRequest(getDutyNoticeConfig, {
    onSuccess: (data) => {
      formData.value = data;
    },
  });

  const { run: runUpdateDutyNoticeConfig } = useRequest(updateDutyNoticeConfig, {
    manual: true,
    onSuccess: (updateResult) => {
      if (updateResult) {
        messageSuccess(t('保存成功'));
        return;
      }
      messageError(t('保存失败'));
    },
  });

  const dateList = [
    {
      value: 'w',
      label: t('按周'),
    },
    {
      value: 'm',
      label: t('按月'),
    },
  ];

  const weekdayList = [
    {
      value: 1,
      label: t('周一'),
    },
    {
      value: 2,
      label: t('周二'),
    },
    {
      value: 3,
      label: t('周三'),
    },
    {
      value: 4,
      label: t('周四'),
    },
    {
      value: 5,
      label: t('周五'),
    },
    {
      value: 6,
      label: t('周六'),
    },
    {
      value: 0,
      label: t('周日'),
    },
  ];

  const periodList = [
    {
      value: 'h',
      label: t('时'),
    },
    {
      value: 'd',
      label: t('天'),
    },
  ];

  const handleSingleMonthDateRangeChange = (list: number[]) => {
    formData.value.schedule_table.send_at.freq_values = list;
  };

  const handleReset = () => {
    formData.value = initData();
  };

  const handleSubmit = () => {
    runUpdateDutyNoticeConfig(formData.value);
  };
</script>

<style lang="less" scoped>

.notification-setting-box {
  padding: 14px 18px;
  background: #FFF;
  border-radius: 2px;
  box-shadow: 0 2px 4px 0 #1919290d;

  .switch-box {
    display: flex;
    width: 100%;
    align-items: center;
    margin-bottom: 14px;

    .title {
      margin-right: 8px;
      color: #313238;
    }
  }

  .item-box{
    display: flex;
    width: 100%;
    margin-bottom: 16px;

    .title {
      width: 100px;
      height: 32px;
      margin-right: 22px;
      line-height: 32px;
      text-align: right;
    }

    .content {
      flex: 1;
      display: flex;
      align-items: center;
      gap: 8px;

      .prefix-box {
        width: 28px;
        height: 30px;
        line-height: 30px;
        text-align: center;
        background: #FAFBFD;
        border-right: 1px solid #C4C6CC;
      }

      .icon {
        font-size: 18px;
        color: #C4C6CC;
        cursor: pointer;

        &:hover {
          color: #979BA5;
        }
      }

      .suffix-box {
        :deep(.bk-input) {
          height: 30px;
          border: none;
        }
      }

      .time-pick {
        position: relative;
        width: 180px;

        :deep(.bk-date-picker-dropdown) {
          top: 36px !important;
          left: 0 !important;
        }
      }
    }
  }
}


.notification-setting-footer {
  margin: 32px 0 0 260px;

  .bk-button {
    width: 88px;
  }
}
</style>
