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
      :label="t('屏蔽类型')"
      property="type"
      required>
      <BkRadioGroup
        :before-change="handleTypeBeforeChange"
        :model-value="formModel.type"
        type="card"
        @change="handleTypeChange">
        <BkRadioButton
          v-for="item in shieldTypeList"
          :key="item.label"
          :label="item.value">
          {{ item.label }}
        </BkRadioButton>
      </BkRadioGroup>
    </BkFormItem>
    <Component
      :is="renderRangeScopeMap[formModel.type]"
      ref="dynamicRef"
      :data="data?.dimension_config"
      :disabled="isEditMode" />
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
    </BkFormItem>
  </BkForm>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import AlarmShieldModel from '@services/model/monitor/alarm-shield';

  import ShieldDateTimePicker from '@views/monitor-alarm/common/ShieldDateTimePicker.vue';

  import { createAlarmShield, EditAlarmShield } from '@/services/source/monitor';

  import AlertShield from './components/AlertShield.vue';
  import DimensionShield from './components/dimension-shield/Index.vue';
  import StrategyShield from './components/StrategyShield.vue';

  interface Props {
    data?: AlarmShieldModel;
    editMode?: string;
  }

  type Emits = (e: 'success') => void;

  interface Exposes {
    cancel: () => Promise<void>;
    submit: () => Promise<number>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    editMode: 'edit',
  });

  const emits = defineEmits<Emits>();

  const initFormModel = () => ({
    datetime: ['', ''] as [string, string],
    dimensions: [1],
    level: [1],
    range: [1],
    reason: '',
    type: 'strategy',
  });

  const { t } = useI18n();

  const formRef = ref();
  const dynamicRef = ref();
  const formModel = ref(initFormModel());

  const isEditMode = computed(() => props.editMode === 'edit');
  const isDisabled = computed(() => !!props.data?.category && ['alert', 'scope'].includes(props.data.category));

  const shieldTypeList = computed(() => {
    const baseList = [
      {
        label: t('基于策略屏蔽'),
        value: 'strategy',
      },
      {
        label: t('基于维度屏蔽'),
        value: 'dimension',
      },
    ];
    const alertItem = {
      label: t('基于事件屏蔽'),
      value: 'alert',
    };
    if (props.data?.category === 'alert') {
      return [alertItem, ...baseList];
    }

    return baseList;
  });

  const renderRangeScopeMap: Record<string, any> = {
    alert: AlertShield,
    dimension: DimensionShield,
    scope: DimensionShield,
    strategy: StrategyShield,
  };

  const rules = {
    datetime: [
      {
        message: t('n不能为空', { n: t('屏蔽时间') }),
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
    dimensions: [
      {
        message: t('至少选择2个维度'),
        trigger: 'blur',
        validator: () => {
          const dataInfo = dynamicRef.value.getValue('dimension');
          if (formModel.value.type === 'dimension') {
            return dataInfo.dimension_config.dimension_conditions.length > 1;
          }

          return true;
        },
      },
      {
        message: t('维度信息不全'),
        trigger: 'blur',
        validator: () => {
          const dataInfo = dynamicRef.value.getValue('dimension');
          return dataInfo.dimension_config.dimension_conditions.every(
            (item: { key: string; value: string[] }) => !!item.key && !!item.value.length,
          );
        },
      },
    ],
    level: [
      {
        message: t('n不能为空', { n: t('告警等级') }),
        trigger: 'blur',
        validator: () => {
          const dataInfo = dynamicRef.value.getValue('dimension');
          return dataInfo.dimension_config.level.length > 0;
        },
      },
    ],
    range: [
      {
        message: t('n不能为空', { n: t('屏蔽的策略') }),
        trigger: 'blur',
        validator: () => dynamicRef.value.getValue(),
      },
    ],
  };

  watchEffect(() => {
    if (props.data) {
      formModel.value.type = props.data.category === 'scope' ? 'dimension' : props.data.category;
      formModel.value.datetime = [props.data.begin_time, props.data.end_time];
      formModel.value.level = props.data.dimension_config.level;
      formModel.value.reason = props.data.description;
      return;
    }

    formModel.value = initFormModel();
  });

  watch(
    formModel,
    () => {
      window.changeConfirm = true;
    },
    {
      deep: true,
    },
  );

  const handleTypeBeforeChange = () => {
    if (props.editMode !== 'create') {
      return false;
    }

    return true;
  };

  const handleTypeChange = (type: string) => {
    if (props.editMode !== 'create') {
      return;
    }

    formModel.value.type = type;
  };

  const handleChoosedShieldDate = () => {
    formRef.value.validate('datetime');
  };

  defineExpose<Exposes>({
    cancel() {
      return Promise.resolve();
    },
    submit() {
      return new Promise((resolve, reject) => {
        formRef.value
          .validate()
          .then(() => {
            const requestHandler = isEditMode.value ? EditAlarmShield : createAlarmShield;
            const dimensionConfig = dynamicRef.value.getValue();
            const params = {
              begin_time: formModel.value.datetime[0],
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              category: formModel.value.type,
              cycle_config: { begin_time: '', day_list: [], end_time: '', type: 1, week_list: [] },
              description: formModel.value.reason,
              end_time: formModel.value.datetime[1],
              notice_config: {},
              shield_notice: false,
              ...dimensionConfig,
            };
            if (isEditMode.value) {
              params.id = props.data!.id;
              params.level = params.dimension_config.level;
              delete params.dimension_config;
            }
            return requestHandler(params).then(() => {
              emits('success');
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

    .bk-checkbox-label {
      display: flex;
      align-items: center;

      .sign-bar {
        display: inline-block;
        width: 4px;
        height: 12px;
        margin-right: 5px;
        border-radius: 1px;

        &.sign-bar-info {
          background: #3a84ff;
        }

        &.sign-bar-warning {
          background: #e38b02;
        }

        &.sign-bar-critical {
          background: #ea3636;
        }
      }
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
