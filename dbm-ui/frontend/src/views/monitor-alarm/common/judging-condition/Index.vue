<template>
  <div class="judging-condition">
    <div class="judging-condition-label">
      <span class="label-content">{{ t('判断条件') }}</span>
      <span class="label-append ml-16">({{ t('判断最终是否要产生告警') }})</span>
    </div>
    <div class="judging-condition-wrapper mt-12">
      <BkFormItem
        item-type="default"
        :label="t('触发条件')"
        label-position="right"
        property="detectsConfig.trigger_config"
        :rules="rules.triggerConfig">
        <I18nT
          class="judging-condition-content"
          keypath="在{0}个周期内累计满足{1}次检测算法，触发告警通知"
          tag="div">
          <BkInput
            v-model="modelValue.detectsConfig.trigger_config.check_window"
            behavior="simplicity"
            class="small-input"
            :disabled="disabled"
            :show-control="false"
            size="small"
            type="number" />
          <BkInput
            v-model="modelValue.detectsConfig.trigger_config.count"
            behavior="simplicity"
            class="small-input"
            :disabled="disabled"
            :show-control="false"
            size="small"
            type="number" />
        </I18nT>
      </BkFormItem>
      <BkFormItem
        item-type="default"
        :label="t('恢复条件')"
        property="detectsConfig.recovery_config"
        :rules="rules.recoveryConfig">
        <I18nT
          class="judging-condition-content"
          keypath="连续{0}个周期内不满足触发条件{1}"
          tag="div">
          <BkInput
            v-model="modelValue.detectsConfig.recovery_config.check_window"
            behavior="simplicity"
            class="small-input"
            :disabled="disabled"
            :show-control="false"
            size="small"
            type="number" />
          <BkCheckbox
            v-model="modelValue.detectsConfig.recovery_config.status_setter"
            class="ml-4"
            :disabled="disabled"
            false-label="recovery"
            true-label="recovery-nodata">
            <span
              :class="{
                'nodata-unchecked': modelValue.detectsConfig.recovery_config.status_setter === 'recovery',
              }">
              {{ t('或无数据') }}
            </span>
          </BkCheckbox>
        </I18nT>
      </BkFormItem>
      <BkFormItem
        item-type="default"
        :label="t('无数据')"
        property="noDataConfig"
        :rules="rules.noDataConfig">
        <I18nT
          v-bk-loading="{ loading: loading }"
          class="judging-condition-content"
          keypath="{0}当数据连续丢失{1}个周期时，触发告警通知基于以下维度{2}进行判断，告警级别{3}"
          tag="div">
          <BkSwitcher
            v-model="modelValue.noDataConfig.is_enabled"
            v-bk-tooltips="{
              content: t('只有监控指标可配置无数据'),
              placement: 'top',
              disabled: nodataConfigTooltipDisabled,
            }"
            class="mr-8"
            :disabled="nodataConfigDisabled"
            size="small"
            theme="primary" />
          <BkInput
            v-model="modelValue.noDataConfig.continuous"
            v-bk-tooltips="{
              content: t('先打开无数据功能'),
              placement: 'top',
              disabled: nodataConfigItemTooltipsDisabled,
            }"
            behavior="simplicity"
            class="small-input"
            :disabled="nodataConfigItemDisabled"
            :show-control="false"
            type="number" />
          <BkTagInput
            v-if="isAggDimensionInput"
            v-model="modelValue.noDataConfig.agg_dimension"
            v-bk-tooltips="{
              content: t('先打开无数据功能'),
              placement: 'top',
              disabled: nodataConfigItemTooltipsDisabled,
            }"
            allow-create
            class="small-select"
            collapse-tags
            :disabled="nodataConfigItemDisabled"
            has-delete-icon
            :placeholder="t('输入')"
            trigger="focus" />
          <BkSelect
            v-else
            v-model="modelValue.noDataConfig.agg_dimension"
            v-bk-tooltips="{
              content: nodataConfigItemDisabled
                ? t('先打开无数据功能')
                : modelValue.noDataConfig.agg_dimension.join(','),
              placement: 'top',
              disabled: nodataConfigItemTooltipsDisabled,
            }"
            behavior="simplicity"
            class="small-select no-data-config-agg-dimension"
            collapse-tags
            :disabled="nodataConfigItemDisabled"
            filterable
            multiple
            multiple-mode="tag"
            show-select-all>
            <BkOption
              v-for="item in aggDimensionList"
              :id="item.id"
              :key="item.id"
              v-bk-tooltips="{
                content: item.id,
                placement: 'right',
              }"
              :name="item.name" />
          </BkSelect>
          <BkSelect
            v-model="modelValue.noDataConfig.level"
            v-bk-tooltips="{
              content: t('先打开无数据功能'),
              placement: 'top',
              disabled: nodataConfigItemTooltipsDisabled,
            }"
            behavior="simplicity"
            class="small-select no-data-config-level"
            :clearable="false"
            :disabled="nodataConfigItemDisabled || loading"
            style="width: 72px">
            <BkOption
              v-for="(item, index) in levelList"
              :id="item.level"
              :key="index"
              :name="item.label" />
          </BkSelect>
        </I18nT>
      </BkFormItem>
      <BkFormItem
        item-type="default"
        :label="t('生效时间段')"
        property="detectsConfig.trigger_config.uptime.time_ranges"
        :rules="rules.timeRanges">
        <TimeRangePicker
          v-model="modelValue.detectsConfig.trigger_config.uptime.time_ranges"
          :disabled="disabled" />
      </BkFormItem>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { searchAlarmStrategy } from '@services/source/monitor';

  import TimeRangePicker from './components/TimeRangePicker.vue';

  interface Props {
    disabled?: boolean;
    monitorPolicyId: number;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    detectsConfig: {
      recovery_config: MonitorPolicyModel['detects_config']['recovery_config'];
      trigger_config: {
        uptime: {
          active_calendars: string[];
          calendars: string[];
          time_ranges: [string, string][];
        };
      } & Omit<MonitorPolicyModel['detects_config']['trigger_config'], 'uptime'>;
    };
    noDataConfig: MonitorPolicyModel['no_data_config'];
  }>({
    required: true,
  });

  const { t } = useI18n();

  const levelList = [
    {
      label: t('致命'),
      level: 1,
    },
    {
      label: t('预警'),
      level: 2,
    },
    {
      label: t('提醒'),
      level: 3,
    },
  ];

  const rules = {
    noDataConfig: [
      {
        message: t('周期数不得小于5且不得大于60'),
        trigger: 'blur',
        validator: () => {
          const { continuous } = modelValue.value.noDataConfig;
          if (nodataConfigDisabled.value) {
            return true;
          }
          return _.isNumber(continuous) && continuous >= 5 && continuous <= 60;
        },
      },
    ],
    recoveryConfig: [
      {
        message: t('恢复条件参数不得小于1'),
        trigger: 'blur',
        validator: () => {
          const { check_window: checkWindow } = modelValue.value.detectsConfig.recovery_config;
          return _.isNumber(checkWindow) && checkWindow > 0;
        },
      },
    ],
    timeRanges: [
      {
        message: t('选择生效时间段'),
        trigger: 'blur',
        validator: () => {
          const { time_ranges: timeRanges } = modelValue.value.detectsConfig.trigger_config.uptime;
          return timeRanges.length > 0;
        },
      },
    ],
    triggerConfig: [
      {
        message: t('触发周期数 >=1 且 >= 检测数'),
        trigger: 'blur',
        validator: () => {
          const { check_window: checkWindow, count } = modelValue.value.detectsConfig.trigger_config;
          return _.isNumber(checkWindow) && _.isNumber(count) && checkWindow > 0 && count > 0 && checkWindow >= count;
        },
      },
    ],
  };

  const aggDimensionList = shallowRef<
    {
      id: string;
      name: string;
    }[]
  >([]);

  const nodataConfigDisabled = computed(
    () => props.disabled || alarmStrategyData.value?.data_source_list?.[0].data_type_label !== 'time_series',
  );
  const nodataConfigTooltipDisabled = computed(() => props.disabled || !nodataConfigDisabled.value);
  const nodataConfigItemDisabled = computed(
    () => props.disabled || nodataConfigDisabled.value || !modelValue.value.noDataConfig.is_enabled,
  );
  const nodataConfigItemTooltipsDisabled = computed(
    () => props.disabled || !nodataConfigItemDisabled.value || modelValue.value.noDataConfig.is_enabled,
  );
  const isAggDimensionInput = computed(
    () => alarmStrategyData.value?.data_source_list?.[0].data_source_label === 'prometheus',
  );

  const {
    data: alarmStrategyData,
    loading,
    run: runSearchAlarmStrategy,
  } = useRequest(searchAlarmStrategy, {
    manual: true,
    onSuccess: (alarmStrategyResult) => {
      const { agg_dimension: aggDimension, metric_list: metricList } = alarmStrategyResult;
      const metricMap = metricList.reduce(
        (prev, cur) => {
          cur.dimensions.forEach((dimensionItem) => {
            if (!prev[dimensionItem.id]) {
              return Object.assign(prev, { [dimensionItem.id]: dimensionItem.name });
            }
          });
          return prev;
        },
        {} as Record<string, string>,
      );

      aggDimensionList.value = aggDimension.reduce<UnwrapRef<typeof aggDimensionList>>((prev, cur) => {
        if (metricMap[cur]) {
          return prev.concat({ id: cur, name: metricMap[cur] });
        }
        return prev;
      }, []);
    },
  });

  watch(
    () => [props.disabled, props.monitorPolicyId],
    () => {
      if (!props.disabled) {
        runSearchAlarmStrategy({
          monitor_policy_id: props.monitorPolicyId,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less">
  .judging-condition {
    margin-bottom: 24px;
    font-size: 12px;

    .judging-condition-label {
      .label-content {
        position: relative;
        font-weight: 700;

        &::after {
          position: absolute;
          top: 0;
          width: 14px;
          color: #ea3636;
          text-align: center;
          content: '*';
        }
      }

      .label-append {
        color: #979ba5;
      }
    }

    .judging-condition-wrapper {
      padding: 12px 24px 0 0;
      border: 1px solid #dcdee5;
      border-radius: 2px;

      .bk-form-item {
        margin-bottom: 12px;
      }

      .bk-form-label {
        width: 100px;
      }

      .bk-form-error {
        left: 100px;
      }

      .is-error .no-data-config-level .bk-input {
        border-color: transparent;
        border-bottom-color: #c4c6cc;
      }

      .judging-condition-content {
        display: flex;
        align-items: center;

        .small-input {
          width: 64px;
          margin: 0 6px;

          & input {
            text-align: center;
          }
        }

        .small-select {
          max-width: 280px;
          min-width: 72px;
          margin: 0 6px;
        }

        .nodata-unchecked {
          color: #979ba5;
        }

        .no-data-config-agg-dimension {
          width: 280px;
        }
      }

      .bk-select .bk-select-trigger .bk-select-tag.is-disabled {
        border-color: transparent;
        border-bottom-color: #dcdee5;
      }

      .bk-select.is-focus:not(.is-disabled).simplicity .bk-select-trigger .bk-select-tag {
        background-color: #fff;
        border-color: #3a84ff;
      }
    }
  }
</style>
