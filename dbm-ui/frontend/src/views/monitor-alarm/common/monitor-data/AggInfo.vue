<template>
  <div class="metric-box">
    <div
      v-for="(item, index) in localValue"
      :key="index"
      class="metric-row">
      <!-- <div
        v-if="isMultiple"
        class="metric-label-tag">
        {{ numberToLetter(index) }}
      </div> -->
      <div>
        <div class="metric-content">
          <span class="metric-label" />
          <span class="metric-label-text">{{
            isMultiple ? t('指标 n', { n: numberToLetter(index) }) : t('指标')
          }}</span>
          <BkInput
            behavior="simplicity"
            readonly
            style="width: 320px; flex-shrink: 0"
            :value="metricMap[item.metric_id] || item.metric_field || item.metric_id" />
          <span class="metric-label-text">{{ t('汇聚方法') }}</span>
          <BkSelect
            v-model="item.agg_method"
            behavior="simplicity"
            class="sf-select"
            :clearable="false"
            :disabled="isMultiple"
            @change="handleChange">
            <BkOption
              v-for="methodItem in METHOD_LIST"
              :key="methodItem.id"
              :value="methodItem.name">
              {{ methodItem.name }}
            </BkOption>
          </BkSelect>
          <span class="metric-label-text">{{ t('汇聚周期') }}</span>
          <BkSelect
            v-model="item.interval"
            behavior="simplicity"
            class="sf-select"
            :clearable="false"
            @change="handleChange">
            <BkOption
              v-for="timeItem in timeList"
              :key="timeItem.seconds"
              :name="timeItem.name"
              :value="timeItem.seconds">
              {{ timeItem.name }}
            </BkOption>
          </BkSelect>
        </div>
        <!-- <div class="metric-desc">
          {{ metricMap[item.metric_id] || item.metric_field || item.metric_id }}
        </div> -->
      </div>
    </div>
    <div
      v-if="isMultiple"
      class="metric-express mt-16">
      <!-- <span class="expr-icon">↳</span> -->
      <span class="expr-label">{{ t('表达式') }}</span>
      <BkInput
        class="expr-input"
        :model-value="expression"
        placeholder=""
        readonly
        style="color: #979ba5; cursor: not-allowed; background: #fafbfd; border-color: #dcdee5" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { searchAlarmStrategy } from '@services/source/monitor';

  interface Props {
    data: MonitorPolicyModel['agg_info'];
    expression: string;
    isMultiple: boolean;
    monitorPolicyId: number;
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    getValue: () => Props['data'];
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const METHOD_LIST = [
    {
      id: 'SUM',
      name: 'SUM',
    },
    {
      id: 'AVG',
      name: 'AVG',
    },
    {
      id: 'MAX',
      name: 'MAX',
    },
    {
      id: 'MIN',
      name: 'MIN',
    },
    {
      id: 'COUNT',
      name: 'COUNT',
    },
  ];

  const timeList = [
    { name: '10 s', seconds: 10 },
    { name: '20 s', seconds: 20 },
    { name: '30 s', seconds: 30 },
    { name: '60 s', seconds: 60 },
    // { name: '1 m', seconds: 1 * 60 },
    { name: '2 m', seconds: 2 * 60 },
    { name: '5 m', seconds: 5 * 60 },
    { name: '10 m', seconds: 10 * 60 },
    { name: '30 m', seconds: 30 * 60 },
    { name: '60 m', seconds: 60 * 60 },
  ];

  const localValue = ref<({ interval: number } & Props['data'][number])[]>([]);

  const metricMap = computed(() =>
    Object.fromEntries(
      (alarmStrategyData.value?.metric_list || []).map((item) => [item.metric_id, item.metric_field_name]),
    ),
  );

  const { data: alarmStrategyData, run: runSearchAlarmStrategy } = useRequest(searchAlarmStrategy, {
    manual: true,
  });

  watch(
    () => props.data,
    () => {
      localValue.value = _.cloneDeep(props.data).map((item) => ({
        ...item,
        interval: item.agg_interval,
      }));
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [props.monitorPolicyId],
    () => {
      runSearchAlarmStrategy({
        monitor_policy_id: props.monitorPolicyId,
      });
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    emits('change');
  };

  const numberToLetter = (num: number): string => {
    return String.fromCharCode('a'.charCodeAt(0) + num);
  };

  defineExpose<Exposes>({
    getValue() {
      return localValue.value.map((item) => _.omit(Object.assign(item, { agg_interval: item.interval }), 'interval'));
    },
  });
</script>

<style lang="less">
  .metric-box {
    font-size: 12px;
    color: #4d4f56;

    .metric-row {
      // display: flex;
      // padding: 16px;
      // border: 1px solid #dcdee5;
      // border-radius: 4px;

      &:not(:first-child) {
        margin-top: 16px;
      }

      .metric-label-tag {
        align-items: center;
        display: inline-flex;
        width: 22px;
        height: 22px;
        margin-top: 4px;
        margin-right: 8px;
        font-size: 12px;
        font-weight: bolder;
        color: #ff9c01;
        background: #ffe8c3;
        border-radius: 50%;
        justify-content: center;
      }

      .metric-content {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-wrap: nowrap;
      }

      .metric-label-text {
        font-size: 12px;
        color: #4d4f56;
        white-space: nowrap;

        &::after {
          margin-left: 4px;
          color: #ea3636;
          content: '*';
        }
      }

      .metric-desc {
        margin-top: 4px;
        margin-left: 58px;
        font-size: 12px;
        color: #979ba5;
      }
    }

    .metric-express {
      display: flex;
      // padding: 12px 16px;
      // margin-bottom: 12px;
      // background: #fafbfd;
      // border: 1px dashed #dcdee5;
      // border-radius: 4px;
      align-items: center;
      gap: 8px;

      .expr-icon {
        font-size: 16px;
        color: #ff9c01;
      }

      .expr-label {
        margin-right: 6px;
        margin-left: 8px;
        font-size: 12px;
        white-space: nowrap;

        &::after {
          margin-left: 4px;
          color: #ea3636;
          content: '';
        }
      }
    }
  }
</style>
