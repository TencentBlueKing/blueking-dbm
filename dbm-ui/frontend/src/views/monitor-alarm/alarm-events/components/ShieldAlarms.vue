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
  <BkForm
    ref="formRef"
    form-type="vertical"
    :model="formModel"
    :rules="rules">
    <BkFormItem
      :label="t('屏蔽范围')"
      required>
      <BkRadioGroup
        v-model="formModel.range"
        :disabled="isDisabled">
        <BkRadio
          v-for="item in alarmRangeList"
          :key="item.label"
          :label="item.value">
          {{ item.label }}
        </BkRadio>
      </BkRadioGroup>
    </BkFormItem>
    <BkFormItem
      :label="t('屏蔽时间')"
      property="datetime"
      required>
      <div class="shield-date-subtitle">({{ t('最长不超过6个月') }})</div>
      <ShieldDateTimePicker
        v-model="formModel.datetime"
        :disabled="isDisabled"
        @finish="handleChoosedShieldDate" />
    </BkFormItem>
    <BkFormItem :label="t('告警内容')">
      <BkAlert
        v-if="isCurrentEvent"
        theme="info"
        :title="t('屏蔽的是告警内容的该类事件，不仅仅当前的事件还包括后续屏蔽时间内产生的事件')" />
      <BkAlert
        v-else
        theme="info"
        :title="t('屏蔽的是这个 IP 或实例产生的所有事件，不仅仅当前的事件还包括后续屏蔽时间内产生的事件')" />
      <div class="alarm-content-main">
        <div class="alarm-item">
          <div class="item-title">{{ t('策略名称') }}:</div>
          <div class="item-content">
            <span>{{ data?.alert_name }}</span>
          </div>
        </div>
        <div
          v-if="isCurrentEvent"
          class="alarm-item">
          <div class="item-title">{{ t('告警级别') }}:</div>
          <div class="item-content">{{ data?.severityDisplayName }}</div>
        </div>
        <div class="alarm-item">
          <div class="item-title">{{ t('所属业务') }}:</div>
          <div class="item-content">{{ bizDisplay }}</div>
        </div>
        <div class="alarm-item">
          <div class="item-title">{{ t('所属集群') }}:</div>
          <div class="item-content">{{ data?.cluster }}</div>
        </div>
        <div
          v-if="isCurrentEvent"
          class="alarm-item">
          <div class="item-title">{{ t('触发条件') }}:</div>
          <div class="item-content">{{ data?.description }}</div>
        </div>
      </div>
    </BkFormItem>
    <BkFormItem
      :label="t('屏蔽原因')"
      property="reason">
      <BkInput
        v-model="formModel.reason"
        autosize
        :disabled="isDisabled"
        :maxlength="100"
        :over-max-length-limit="false"
        :resize="false"
        type="textarea" />
      <div class="quick-input-main">
        <span>{{ t('快捷输入') }}：</span>
        <BkTag
          v-for="(item, index) in quickReasonList"
          :key="index"
          class="quick-choose-item"
          @click="() => handleClickQuickReasonItem(item)">
          {{ item }}
        </BkTag>
      </div>
    </BkFormItem>
  </BkForm>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { createAlarmShield, getAlarmShieldDetails } from '@services/source/monitor';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import ShieldDateTimePicker from '@views/monitor-alarm/common/ShieldDateTimePicker.vue';

  import { messageSuccess } from '@utils';

  import type { RowData } from '../Index.vue';

  interface Props {
    data?: RowData;
  }

  type Emits = (e: 'success') => void;

  interface Exposes {
    cancel: () => void;
    checkValueChange: () => boolean;
    reset: () => void;
    submit: () => Promise<number>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const initFormModel = () => ({
    datetime: ['', ''] as [string, string],
    range: 'alert',
    reason: '',
  });

  const { t } = useI18n();
  const { bizs } = useGlobalBizs();

  const formRef = ref();
  const formModel = ref(initFormModel());

  const isCurrentEvent = computed(() => formModel.value.range === 'alert');
  const isDisabled = computed(() => props.data?.is_shielded);
  const bizsMap = computed(() =>
    bizs.reduce<Record<number, string>>((results, item) => {
      Object.assign(results, {
        [item.bk_biz_id]: item.name,
      });
      return results;
    }, {}),
  );
  const bizDisplay = computed(() => {
    if (!props.data) {
      return '--';
    }

    const bizObj = props.data.dimensions.find((item) => item.key === 'tags.appid');
    if (!bizObj) {
      return '--';
    }

    return bizsMap.value[Number(bizObj.value)] ?? '--';
  });

  const { run: fetchAlarmShieldDetails } = useRequest(getAlarmShieldDetails, {
    manual: true,
    onSuccess: (data) => {
      formModel.value.range = data.category;
      formModel.value.datetime = [data.begin_time, data.end_time];
      formModel.value.reason = data.description;
    },
  });

  const rules = {
    datetime: [
      {
        message: t('屏蔽时间不能为空'),
        trigger: 'blur',
        validator: (value: [string, string]) => value.every((item) => !!item),
      },
      {
        message: t('最长不超过6个月'),
        trigger: 'blur',
        validator: (value: [string, string]) => {
          const [start, end] = value;
          return dayjs(end).diff(start, 'month') <= 6;
        },
      },
    ],
  };

  const alarmRangeList = [
    {
      label: t('当前事件'),
      value: 'alert',
    },
    {
      label: t('整个集群'),
      value: 'strategy',
    },
  ];

  const quickReasonList = [t('变更中，不需要提醒'), t('无关紧要，不需要提醒'), t('已知问题，不需要提醒')];

  watch(
    () => props.data,
    () => {
      if (props.data?.shield_id?.length) {
        fetchAlarmShieldDetails({ id: props.data.shield_id[0] });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    formModel,
    () => {
      window.changeConfirm = true;
    },
    {
      deep: true,
    },
  );

  const handleChoosedShieldDate = () => {
    formRef.value.validate('datetime');
  };

  const handleClickQuickReasonItem = (reason: string) => {
    if (isDisabled.value) {
      return;
    }

    formModel.value.reason = reason;
  };

  const checkValueChange = () => {
    if (isDisabled.value) {
      return false;
    }

    return !_.isEqual(formModel.value, initFormModel());
  };

  defineExpose<Exposes>({
    cancel() {
      const beforeClose = useBeforeClose();
      const isValueChange = checkValueChange();
      return beforeClose(isValueChange);
    },
    checkValueChange() {
      return checkValueChange();
    },
    reset() {
      formModel.value = initFormModel();
    },
    submit() {
      return new Promise((resolve, reject) => {
        formRef.value
          .validate()
          .then(() => {
            const params = {
              begin_time: formModel.value.datetime[0],
              bk_biz_id: props.data!.bk_biz_id,
              category: formModel.value.range,
              cycle_config: {
                begin_time: '',
                day_list: [],
                end_time: '',
                type: 1,
                week_list: [],
              },
              description: formModel.value.reason,
              dimension_config: {
                dimension_conditions: [],
                id: [props.data!.strategy_id],
                level: [props.data!.severity],
              } as any,
              end_time: formModel.value.datetime[1],
              notice_config: {},
              shield_notice: false,
            };
            if (formModel.value.range === 'alert') {
              // 当前事件
              delete params.dimension_config.id;
              params.dimension_config.alert_id = props.data!.id;
              params.dimension_config.dimension_conditions = props.data!.dimensions.map((item) => ({
                condition: 'and',
                key: item.key,
                method: 'eq',
                name: item.display_key,
                value: [item.value],
              }));
            } else {
              const domianDimension = props.data!.dimensions.find((item) => item.key === 'tags.cluster_domain')!;
              const bizDimension = props.data!.dimensions.find((item) => item.key === 'tags.appid')!;
              params.dimension_config.dimension_conditions = [
                {
                  condition: 'and',
                  key: 'cluster_domain',
                  method: 'eq',
                  name: domianDimension.display_key,
                  value: [domianDimension.value],
                },
                {
                  condition: 'and',
                  key: 'appid',
                  method: 'eq',
                  name: bizDimension.display_key,
                  value: [bizDimension.value],
                },
              ];
            }
            return createAlarmShield(params).then(() => {
              emits('success');
              messageSuccess(t('新建告警屏蔽成功'));
              resolve(1);
            });
          })
          .catch(() => {
            reject(1);
          });
      });
    },
  });
</script>

<style lang="less">
  .shiled-alarm-page {
    .bk-modal-content {
      padding: 20px 24px;

      .bk-form-label {
        font-weight: 700;
      }
    }

    .alarm-content-main {
      padding: 8px 25px;
      margin-top: 8px;
      font-size: 12px;
      background: #f5f7fa;
      border-radius: 2px;

      .alarm-item {
        display: flex;
        width: 100%;
        padding: 6px 0;
        line-height: 20px;

        .item-title {
          width: 60px;
        }

        .item-content {
          flex: 1;
          flex-wrap: wrap;

          .link-icon {
            margin-left: 5px;
            color: #3a84ff;
            cursor: pointer;
          }
        }
      }
    }
  }

  .quick-input-main {
    display: flex;
    margin-top: 8px;
    font-size: 12px;
    align-items: center;

    .quick-choose-item {
      margin-right: 4px;
      cursor: pointer;
    }
  }

  .shield-date-subtitle {
    position: absolute;
    top: -32px;
    left: 65px;
    font-size: 12px;
    color: #979ba5;
  }
</style>
