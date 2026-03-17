<template>
  <div class="detect-rule-card">
    <div class="card-header">
      <div class="header-left">
        <!-- <span
          class="level-dot"
          :class="[levelClass]"
          :style="{ backgroundColor: levelColor }" /> -->
        <!-- <DbIcon type="warn-lightning" /> -->
        <span class="header-title"> {{ t('静态阈值') }} </span>
      </div>
      <DbIcon
        v-if="showDelete"
        class="card-delete"
        type="delete"
        @click="handleDelete" />
    </div>
    <div class="card-body">
      <div class="form-row">
        <span class="form-label">{{ t('告警级别') }}</span>
        <!-- <span
          class="level-dot"
          :class="[levelClass]"
          :style="{ backgroundColor: levelColor }" /> -->
        <BkSelect
          v-model="localLevel"
          behavior="simplicity"
          class="level-select"
          :clearable="false"
          @change="handleLevelChange">
          <template
            v-if="localLevel && currentOptionLevelInfo"
            #prefix>
            <div class="select-prefix">
              <DbIcon
                class="select-prefix-icon"
                :style="{ color: currentOptionLevelInfo.color }"
                :type="currentOptionLevelInfo.icon" />
            </div>
          </template>
          <BkOption
            v-for="option in availableLevelOptions"
            :key="option.value"
            :disabled="option.disabled"
            :label="option.label"
            :value="option.value">
            <div
              v-bk-tooltips="{
                content: t('已使用'),
                disabled: !option.disabled,
              }"
              class="select-option-item">
              <DbIcon
                class="select-option-item-icon mr-4"
                :style="{ color: option.color }"
                :type="option.icon" />
              {{ option.label }}
            </div>
          </BkOption>
        </BkSelect>
      </div>
      <div class="form-row">
        <span class="form-label">{{ t('告警条件') }}</span>
        <div class="condition-group">
          <div
            v-for="(condition, conditionIndex) in localConditions"
            :key="conditionIndex"
            class="condition-item">
            <template v-if="conditionIndex === 0">
              <span class="condition-prefix">（{{ t('当前值') }}）</span>
            </template>
            <template v-else>
              <div
                v-bk-tooltips="t('点击切换 AND / OR')"
                class="logic-tag"
                @click="() => toggleLogicRelation(conditionIndex)">
                {{ condition.conditionRelation }}
              </div>
            </template>
            <BkSelect
              v-model="condition.operator"
              class="operator-select"
              :clearable="false"
              :popover-options="{
                width: '70px',
              }"
              @change="handleConditionChange">
              <template #trigger="{ selected }: { selected: { label: string; value: string }[] }">
                <div class="operator-select-trigger">
                  {{ selected?.[0]?.label }}
                </div>
              </template>
              <BkOption
                v-for="op in operatorOptions"
                :key="op.value"
                :label="op.label"
                :value="op.value" />
            </BkSelect>
            <BkInput
              v-model="condition.value"
              behavior="simplicity"
              class="value-input"
              :placeholder="t('阈值')"
              type="number"
              @change="handleConditionChange" />
            <DbIcon
              v-if="conditionIndex > 0"
              v-bk-tooltips="t('删除条件')"
              class="condition-delete"
              type="close"
              @click="removeCondition(conditionIndex)">
            </DbIcon>
          </div>
          <div
            class="add-condition-btn"
            @click="addCondition">
            <DbIcon type="add" />
          </div>
          <span class="condition-suffix">{{ t('时触发告警') }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  export interface RuleCondition {
    conditionRelation?: 'AND' | 'OR'; // 首个不包含
    operator: string;
    value: string | number;
  }

  export interface RuleData {
    conditions: RuleCondition[];
    level: 1 | 2 | 3; // 1: fatal, 2: warning, 3: info
    unitPrefix: string;
  }

  interface Props {
    allRules: RuleData[];
    data: RuleData;
    index: number;
  }

  interface Exposes {
    getValue: () => RuleData;
  }

  interface Emits {
    (e: 'delete', index: number): void;
    (e: 'change'): void;
  }

  const props = defineProps<Props>();
  const emit = defineEmits<Emits>();
  const { t } = useI18n();

  const levelOptions = [
    { color: '#EA3636', icon: 'alert', label: t('致命'), value: 1 },
    { color: '#FF9C01', icon: 'exclamation-fill', label: t('预警'), value: 2 },
    { color: '#3A84FF', icon: 'attention-fill', label: t('提醒'), value: 3 },
  ];

  const signMap: Record<string, string> = {
    eq: '=',
    gt: '>',
    gte: '>=',
    lt: '<',
    lte: '<=',
    neq: '!=',
  };

  const operatorOptions = Object.entries(signMap).map((item) => ({
    label: item[1],
    value: item[0],
  }));

  const localLevel = ref<1 | 2 | 3>(props.data.level);
  const localConditions = ref<RuleCondition[]>([]);

  watch(
    () => props.data,
    (newData) => {
      localLevel.value = newData.level;
      localConditions.value = newData.conditions?.length
        ? _.cloneDeep(newData.conditions)
        : [{ operator: 'gte', value: '' }];
    },
    {
      immediate: true,
    },
  );

  const showDelete = computed(() => props.allRules.length > 1);

  const usedLevels = computed(() =>
    props.allRules
      .map((rule, i) => (i !== props.index ? rule.level : null))
      .filter((level): level is 1 | 2 | 3 => level !== null),
  );

  const availableLevelOptions = computed(() =>
    levelOptions.map((option) => ({
      ...option,
      disabled: usedLevels.value.includes(option.value as 1 | 2 | 3),
    })),
  );

  const currentOptionLevelInfo = computed(() =>
    availableLevelOptions.value.find((item) => item.value === localLevel.value),
  );

  const handleLevelChange = () => {
    emit('change');
  };

  const handleConditionChange = () => {
    emit('change');
  };

  const handleDelete = () => {
    emit('delete', props.index);
  };

  const addCondition = () => {
    localConditions.value.push({ conditionRelation: 'AND', operator: 'gte', value: 0 });
    emit('change');
  };

  const removeCondition = (index: number) => {
    if (localConditions.value.length <= 1) {
      return;
    }
    localConditions.value.splice(index, 1);
    emit('change');
  };

  const toggleLogicRelation = (index: number) => {
    localConditions.value[index].conditionRelation =
      localConditions.value[index].conditionRelation === 'AND' ? 'OR' : 'AND';
    emit('change');
  };

  defineExpose<Exposes>({
    getValue() {
      return {
        // conditionRelation: localConditionRelation.value,
        conditions: localConditions.value,
        level: localLevel.value,
        unitPrefix: props.data.unitPrefix,
      };
    },
  });
</script>

<style lang="less" scoped>
  .detect-rule-card {
    margin-bottom: 12px;
    overflow: hidden;
    // background: #fafbfd;
    border: 1px solid #dcdee5;
    border-radius: 4px;

    &:hover {
      border-color: #3a84ff;
      transition: all 0.2s;

      .card-header {
        background-color: #f0f5ff;

        .card-delete {
          display: inline-block;
        }
      }
    }

    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 10px 14px;
      font-size: 13px;
      font-weight: 500;
      color: #313238;
      background-color: #f5f7fa;
      // border-bottom: 1px solid #dcdee5;

      .header-left {
        display: flex;
        align-items: center;
        gap: 6px;
      }

      .level-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        flex-shrink: 0;
      }

      .header-title {
        color: #4d4f56;
      }

      .card-delete {
        display: none;
        font-size: 14px;
        color: #ea3636;
      }
    }

    .card-body {
      padding: 14px;

      .form-row {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 10px;
        font-size: 13px;
        color: #313238;

        &:last-child {
          margin-bottom: 0;
        }

        .form-label {
          width: 80px;
          font-size: 12px;
          color: #4d4f56;
          flex-shrink: 0;
          text-align: right;

          &::after {
            margin-left: 4px;
            color: #ea3636;
            content: '*';
          }
        }

        .level-dot {
          width: 8px;
          height: 8px;
          flex-shrink: 0;
          border-radius: 50%;
        }

        .level-select {
          width: 120px;

          .select-prefix {
            padding-left: 4px;
            line-height: 30px;
            text-align: center;

            &:hover {
              background-color: #f5f7fa;
            }

            .select-prefix-icon {
              font-size: 16px;
            }
          }
        }

        .condition-group {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 6px;

          .condition-item {
            display: inline-flex;
            align-items: center;
            gap: 6px;

            .condition-prefix {
              font-size: 12px;
              color: #4d4f56;
              white-space: nowrap;
            }

            .logic-tag {
              width: 38px;
              height: 24px;
              padding: 0 4px;
              line-height: 24px;
              justify-content: center;
              align-items: center;
              gap: 10px;
              color: #3a84ff;
              text-align: center;
              background-color: #e1ecff;
              border-radius: 2px;
            }

            .operator-select {
              // width: 70px;

              .operator-select-trigger {
                width: 24px;
                height: 24px;
                line-height: 24px;
                color: #4d4f56;
                text-align: center;
                background-color: #f0f1f5;
                border-radius: 2px;
              }
            }

            .value-input {
              width: 100px;
            }

            .condition-delete {
              display: inline-flex;
              width: 24px;
              height: 24px;
              align-items: center;
              justify-content: center;
              flex-shrink: 0;
              font-size: 14px;
              color: #979ba5;
              cursor: pointer;
              border-radius: 2px;
              transition: all 0.15s;

              &:hover {
                color: #ea3636;
                background: #fdd;
              }
            }
          }

          .add-condition-btn {
            width: 24px;
            height: 24px;
            font-size: 12px;
            line-height: 24px;
            color: #3a84ff;
            text-align: center;
            cursor: pointer;
            background-color: #e1ecff;
            border-radius: 2px;
            transition: all 0.15s;
          }

          .condition-suffix {
            font-size: 12px;
            color: #4d4f56;
            white-space: nowrap;
          }
        }
      }
    }
  }

  .select-option-item {
    display: flex;

    .select-option-item-icon {
      font-size: 16px;
    }
  }
</style>
