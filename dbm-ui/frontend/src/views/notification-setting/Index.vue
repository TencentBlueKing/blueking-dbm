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
  <BkLoading
    class="notification-setting-box"
    :loading="getLoading">
    <DbTab v-model:active="dbType" />
    <SmartAction :offset-target="getSmartActionOffsetTarget">
      <div class="notification-setting-content">
        <DbForm
          ref="formRef"
          :model="formData">
          <DbFormItem
            :label="t('通知内容')"
            property="after"
            required>
            <BkInput
              v-model="formData.after"
              :clearable="false"
              :max="100"
              :min="1"
              :prefix="t('未来')"
              style="width: 200px"
              type="number">
            </BkInput>
            <span class="input-suffix">{{ t('天的排班表') }}</span>
          </DbFormItem>
          <Channels
            ref="channelsRef"
            :data="formData.channels" />
          <DbFormItem
            :label="t('周期发送')"
            property="enabled">
            <BkSwitcher
              v-model="formData.enabled"
              size="small"
              theme="primary"
              @change="handleChangeEnabled" />
          </DbFormItem>
          <TimeItem
            v-show="formData.enabled"
            ref="timeRef"
            :data="formData.cron" />
        </DbForm>
      </div>
      <template #action>
        <div>
          <AuthButton
            action-id="update_duty_notices_config"
            class="mr-8 w-88"
            :disabled="sendLoading || resetLoading"
            :loading="updateLoading"
            theme="primary"
            @click="handleSave">
            {{ t('保存') }}
          </AuthButton>
          <AuthButton
            action-id="update_duty_notices_config"
            class="mr-8 w-88"
            :disabled="updateLoading || resetLoading"
            :loading="sendLoading"
            @click="handleSend">
            {{ t('立即发送') }}
          </AuthButton>
          <DbPopconfirm
            :confirm-handler="handleReset"
            :content="t('重置将会恢复默认设置的内容！')"
            :title="t('确认重置当前配置？')">
            <span>
              <AuthButton
                action-id="update_duty_notices_config"
                class="w-88"
                :disabled="updateLoading || sendLoading"
                :loading="resetLoading">
                {{ t('重置') }}
              </AuthButton>
            </span>
          </DbPopconfirm>
        </div>
      </template>
    </SmartAction>
  </BkLoading>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getDutyNoticeConfig, sendDutyNoticeSchedule, updateDutyNoticeConfig } from '@services/source/monitor';

  import { DBTypes, MessageTypes } from '@common/const';

  import DbTab from '@components/db-tab/Index.vue';

  import { messageSuccess } from '@utils';

  import Channels from './components/Channels.vue';
  import TimeItem from './components/TimeItem.vue';

  type DutyNoticeConfig = ServiceReturnType<typeof getDutyNoticeConfig>[string];

  const initData = (data?: DutyNoticeConfig) => {
    if (!data) {
      return {
        after: 7,
        channels: {
          [MessageTypes.RTX]: true,
        },
        cron: {
          day_of_month: '*',
          day_of_week: '1',
          hour: '10',
          minute: '0',
        },
        enabled: false,
      };
    }
    return data;
  };

  const { t } = useI18n();

  const formRef = useTemplateRef('formRef');
  const timeRef = useTemplateRef('timeRef');
  const channelsRef = useTemplateRef('channelsRef');

  const dbType = ref(DBTypes.MYSQL);

  const formData = reactive(initData());

  const {
    data: dutyNoticeConfig,
    loading: getLoading,
    run: runGetDutyNoticeConfig,
  } = useRequest(getDutyNoticeConfig, {
    manual: true,
  });

  const { loading: updateLoading, run: runUpdateDutyNoticeConfig } = useRequest(updateDutyNoticeConfig, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('保存成功'));
      runGetDutyNoticeConfig();
    },
  });

  const { loading: sendLoading, run: runSendDutyNoticeSchedule } = useRequest(sendDutyNoticeSchedule, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('发送成功'));
    },
  });

  const { loading: resetLoading, run: runResetDutyNoticeConfig } = useRequest(updateDutyNoticeConfig, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('重置成功'));
      runGetDutyNoticeConfig();
    },
  });

  watch(
    [dbType, dutyNoticeConfig],
    () => {
      if (dutyNoticeConfig.value && _.has(dutyNoticeConfig.value, dbType.value)) {
        Object.assign(formData, initData(dutyNoticeConfig.value[dbType.value]));
      } else {
        Object.assign(formData, initData());
      }
    },
    {
      immediate: true,
    },
  );

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const handleChangeEnabled = (value: boolean) => {
    if (value) {
      Object.assign(formData, { cron: initData().cron });
    }
  };

  const handleSave = () => {
    formRef.value!.validate().then(() => {
      const params = {
        after: formData.after,
        channels: channelsRef.value!.getValue(),
        cron: timeRef.value!.getValue(),
        db_type: dbType.value,
        enabled: formData.enabled,
      };
      runUpdateDutyNoticeConfig(params);
    });
  };

  const handleSend = () => {
    runSendDutyNoticeSchedule({ db_type: dbType.value });
  };

  const handleReset = () => {
    runResetDutyNoticeConfig({ ...initData(), db_type: dbType.value });
  };

  onMounted(() => {
    runGetDutyNoticeConfig();
  });
</script>

<style lang="less">
  .notification-setting-box {
    .notification-setting-content {
      padding: 24px;
      margin: 20px 28px 32px;
      background: #fff;
      border-radius: 2px;
      box-shadow: 0 2px 4px 0 #1919290d;
    }

    .bk-form-label {
      font-size: 12px;
      color: #4d4f56;
    }

    .input-suffix {
      margin-left: 8px;
      font-size: 12px;
      color: #4d4f56;
    }
  }
</style>
