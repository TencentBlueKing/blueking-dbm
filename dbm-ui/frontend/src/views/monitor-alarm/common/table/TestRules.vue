<template>
  <div class="monitor-test-rules">
    <div
      v-for="item in dataList"
      :key="item.level">
      <DbIcon
        class="level-icon mr-4"
        :style="{ color: levelMap[item.level].color }"
        :type="levelMap[item.level].icon" />
      <span>{{ levelMap[item.level].label }}：</span>
      <span
        v-for="(configItem, configIndex) in formatConfig(item.config)"
        :key="configIndex">
        {{ configItem.conditionRelation ? ` ${configItem.conditionRelation} ` : '' }}
        {{ signMap[configItem.operator] }}
        {{ configItem.value }}
        {{ item.unit_prefix }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

  interface Props {
    testRules: MonitorPolicyModel['test_rules'];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const levelMap: Record<
    string,
    {
      color: string;
      icon: string;
      label: string;
    }
  > = {
    '1': { color: '#EA3636', icon: 'alert', label: t('致命') },
    '2': { color: '#FF9C01', icon: 'exclamation-fill', label: t('预警') },
    '3': { color: '#3A84FF', icon: 'attention-fill', label: t('提醒') },
  };

  const signMap: Record<string, string> = {
    eq: '=',
    gt: '>',
    gte: '>=',
    lt: '<',
    lte: '<=',
    neq: '!=',
  };

  const formateRule = (data: Props['testRules'], level: number) => {
    const arr = data.filter((item) => item.level === level);
    return arr.length > 0 ? arr[0] : undefined;
  };

  const dangerRule = computed(() => formateRule(props.testRules, 1));
  const warnRule = computed(() => formateRule(props.testRules, 2));
  const infoRule = computed(() => formateRule(props.testRules, 3));

  const dataList = computed(() =>
    [dangerRule.value, warnRule.value, infoRule.value].filter((item) => item !== undefined),
  );

  const formatConfig = (config: Props['testRules'][number]['config']) => {
    const conditions: {
      conditionRelation?: 'AND' | 'OR'; // 首个不包含
      operator: string;
      value: string | number;
    }[] = [];
    config.forEach((configItem, configIndex) => {
      configItem.map((innerItem, innerIndex) => {
        if (configIndex === 0 && innerIndex === 0) {
          // 首个元素不添加连接符
          conditions.push({
            operator: innerItem.method || 'gte',
            value: innerItem.threshold ?? '',
          });
        } else if (innerIndex === 0) {
          // 内层首个元素，连接符为 OR
          conditions.push({
            conditionRelation: 'OR',
            operator: innerItem.method || 'gte',
            value: innerItem.threshold ?? '',
          });
        } else {
          // 其余默认连接符为 AND
          conditions.push({
            conditionRelation: 'AND',
            operator: innerItem.method || 'gte',
            value: innerItem.threshold ?? '',
          });
        }
      });
    });
    return conditions;
  };
</script>

<style lang="less">
  .monitor-test-rules {
    .level-icon {
      font-size: 16px;
    }
  }
</style>
