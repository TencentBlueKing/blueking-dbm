<template>
  <BkCard is-collapse>
    <template #header>
      <span style="font-weight: 600">{{ t('检测规则') }}</span>
      <span style="margin-left: 4px; font-size: 12px; color: #979ba5">
        （{{ t('通过查询的数据按检测规则判断是否需要进行告警') }}）
      </span>
    </template>
    <div class="test-rules-container">
      <!-- <I18nT
        class="connect-select mb-16"
        keypath="同级别的各算法之间是{0}的关系"
        tag="div">
        <BkSelect
          v-model="modelValue"
          class="ml-4 mr-4"
          :clearable="false"
          style="width: 80px">
          <BkOption
            v-for="opt in algorithmRelationship"
            :id="opt.id"
            :key="opt.id"
            :name="opt.name" />
        </BkSelect>
      </I18nT> -->
      <div
        v-for="(rule, index) in localRules"
        :key="index"
        class="rule-item">
        <div
          v-if="index > 0"
          class="rule-separator">
          {{ t('—— 各规则独立判断 ——') }}
        </div>
        <ItemCard
          :ref="(el) => setRuleCardRef(el, index)"
          :all-rules="localRules"
          :data="rule"
          :index="index"
          @delete="removeRule" />
      </div>
      <BkButton
        v-if="showAddButton"
        class="add-btn"
        text
        theme="primary"
        @click="addRule">
        <DbIcon
          class="mr-4 mt-2"
          type="add" />
        {{ t('检测规则') }}
      </BkButton>
    </div>
  </BkCard>
</template>

<script setup lang="ts">
  import { computed, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

  import DbIcon from '@components/db-icon';

  import ItemCard, { type RuleCondition, type RuleData } from './ItemCard.vue';

  interface Props {
    rules?: MonitorPolicyModel['test_rules'];
  }

  interface Exposes {
    getValue: () => MonitorPolicyModel['test_rules'];
  }

  const props = withDefaults(defineProps<Props>(), {
    rules: () => [],
  });

  // const modelValue = defineModel<string>('connector', { required: true });

  const { t } = useI18n();

  // const algorithmRelationship = [
  //   { id: 'and', name: t('且') },
  //   { id: 'or', name: t('或') },
  // ];

  const ruleCardRefs = ref<InstanceType<typeof ItemCard>[]>([]);

  // 将 test_rules 格式转换为组件内部格式
  const convertToInternalFormat = (rules: MonitorPolicyModel['test_rules']): RuleData[] => {
    if (!rules || rules.length === 0) {
      return [{ conditions: [{ operator: 'gte', value: '' }], level: 1, unitPrefix: '' }];
    }

    return rules.map((rule) => {
      const conditions: RuleCondition[] = [];

      // test_rules.config 是二维数组：外层 OR，内层 AND
      if (rule.config && rule.config.length > 0) {
        rule.config.forEach((configItem, configIndex) => {
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
      }

      if (conditions.length === 0) {
        conditions.push({ operator: 'gte', value: '' });
      }

      return {
        conditions,
        level: rule.level as 1 | 2 | 3,
        unitPrefix: rule.unit_prefix,
      };
    });
  };

  // 将组件内部格式转换回 test_rules 格式
  const convertToExternalFormat = (rules: RuleData[]): MonitorPolicyModel['test_rules'] => {
    return rules.map((rule) => {
      // 将 conditions 转换为 config 格式
      // OR 关系：每个条件单独一组
      // AND 关系：所有条件在同一组
      const config: { method: string; threshold: number }[][] = [];

      let configItem: { method: string; threshold: number }[] = [];
      rule.conditions.forEach((conditionItem) => {
        // 连接符为 OR，将之前的数据加入总数据数组中，并新加一个数组
        if (conditionItem.conditionRelation === 'OR') {
          config.push(configItem);
          configItem = [];
        }
        configItem.push({
          method: conditionItem.operator || 'gte',
          threshold: Number(conditionItem.value) || 0,
        });
      });

      // 最后一组数据
      config.push(configItem);
      return {
        config,
        level: rule.level,
        type: 'Threshold',
        unit_prefix: rule.unitPrefix,
      };
    });
  };

  const localRules = ref<RuleData[]>(convertToInternalFormat(props.rules));

  const showAddButton = computed(() => localRules.value.length < 3);

  const setRuleCardRef = (el: any, index: number) => {
    if (el) {
      ruleCardRefs.value[index] = el;
    }
  };

  const getAvailableLevel = () => {
    const allLevels: (1 | 2 | 3)[] = [1, 2, 3];
    const usedLevels = localRules.value.map((rule) => rule.level);
    return allLevels.find((level) => !usedLevels.includes(level)) || 3;
  };

  const addRule = () => {
    if (localRules.value.length >= 3) {
      return;
    }

    const newLevel = getAvailableLevel();
    const newRule: RuleData = {
      conditions: [{ operator: 'gte', value: 0 }],
      level: newLevel,
      unitPrefix: '',
    };
    localRules.value.push(newRule);
  };

  const removeRule = (index: number) => {
    if (localRules.value.length <= 1) {
      return;
    }
    localRules.value.splice(index, 1);
    ruleCardRefs.value.splice(index, 1);
  };

  defineExpose<Exposes>({
    getValue() {
      const rules = ruleCardRefs.value.map((ref) => ref.getValue()).filter(Boolean);
      return convertToExternalFormat(rules);
    },
  });
</script>

<style lang="less" scoped>
  .test-rules-container {
    .connect-select {
      display: flex;
      align-items: center;
      font-size: 12px;
    }

    .rule-item {
      position: relative;

      .rule-separator {
        padding: 6px 0;
        font-size: 12px;
        color: #c4c6cc;
        text-align: center;
      }
    }

    .add-btn {
      width: 100%;
      height: 32px;
      padding-left: 32px;
      font-size: 12px;
      justify-content: start;
      border: 1px dashed #c4c6cc;
    }
  }
</style>
