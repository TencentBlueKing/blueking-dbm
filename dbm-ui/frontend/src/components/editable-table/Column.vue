<template>
  <td
    v-if="isRowspanRender"
    ref="rootRef"
    class="bk-editable-table-body-column"
    :class="{
      'is-focused': isFocused,
      'is-error': validateState.isError,
      'is-disabled': Boolean(disabledTips),
      [`is-column-fixed-${fixed}`]: fixed,
      'is-previous-sibling-rowspan': isPreviousSiblingRowspan,
    }"
    :data-name="columnKey"
    :rowspan="rowspan">
    <div
      v-bk-tooltips="{
        content: disabledTips,
        disabled: !disabledTips,
      }"
      class="bk-editable-table-field-cell">
      <slot />
      <div
        v-if="validateState.isError"
        class="bk-editable-table-column-error">
        <slot
          name="error"
          v-bind="{ message: validateState.errorMessage }">
          <i
            v-bk-tooltips="validateState.errorMessage"
            class="bk-dbm db-icon-exclamation-fill" />
        </slot>
      </div>
    </div>
  </td>
</template>
<script lang="ts">
  import get from 'lodash/get';
  import isFunction from 'lodash/isFunction';
  import {
    type ComponentInternalInstance,
    computed,
    getCurrentInstance,
    inject,
    type InjectionKey,
    onBeforeUnmount,
    provide,
    reactive,
    type VNode,
  } from 'vue';

  import { tableInjectKey } from './Index.vue';
  import { injectKey } from './Row.vue';
  import { type IRule } from './types';
  import defaultValidator from './validator';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    field?: string;
    label: string;
    rowspan?: number;
    width?: number;
    minWidth?: number;
    maxWidth?: number;
    rules?: IRule[];
    required?: boolean;
    email?: boolean;
    max?: number;
    min?: number;
    maxlength?: number;
    fixed?: 'left' | 'right';
    disabledMethod?: (rowData?: any, field?: string) => string | boolean;
    description?: string;
  }

  interface Slots {
    default: () => VNode;
    head?: () => VNode;
    headPrepend?: () => VNode;
    headAppend?: () => VNode;
    error?: (params: { message: string }) => VNode;
  }

  interface Expose {
    validate: () => Promise<boolean>;
  }

  const hasOwn = (obj: Record<string, any>, key: string) => Object.prototype.hasOwnProperty.call(obj, key);

  const getRuleMessage = (rule: IRule) => {
    if (typeof rule.message === 'function') {
      return rule.message();
    }
    return rule.message;
  };

  export interface IContext {
    instance: ComponentInternalInstance;
    el: HTMLElement;
    key: string;
    props: Props;
    slots: Slots;
    validate: () => Promise<boolean>;
  }

  export const EditableTableColumnKey: InjectionKey<{
    blur: () => void;
    focus: () => void;
    registerRules: (params: IRule[]) => void;
    validate: () => Promise<boolean>;
    clearValidate: () => void;
  }> = Symbol('EditableTableColumnKey');
</script>
<script setup lang="ts">
  const props = defineProps<Props>();
  const slots = defineSlots<Slots>();

  const tableContext = inject(tableInjectKey);
  const rowContext = inject(injectKey);
  const currentInstance = getCurrentInstance() as ComponentInternalInstance;

  const columnKey = `bk-editable-table-column-${rowContext?.getColumnIndex()}`;

  interface IFinalRule {
    validator: (value: any) => Promise<boolean | string> | boolean | string;
    message: string | (() => string);
    trigger: string;
  }

  const getRulesFromProps = (props: Props) => {
    const rules: (IFinalRule & {
      required?: boolean;
      email?: boolean;
    })[] = [];

    const label = props.label || '';
    if (props.required) {
      rules.push({
        required: true,
        validator: defaultValidator.required,
        message: `${label}不能为空`,
        trigger: 'change',
      });
    }
    if (props.email) {
      rules.push({
        email: true,
        validator: (value: string) => defaultValidator.email(value),
        message: `${label}不是 email`,
        trigger: 'change',
      });
    }
    if (Number(props.max) > -1) {
      rules.push({
        validator: (value: number) => defaultValidator.max(value, props.max as number),
        message: `${label}最大值 ${props.max}`,
        trigger: 'change',
      });
    }
    if (Number(props.min) > -1) {
      rules.push({
        validator: (value) => defaultValidator.min(value, props.min as number),
        message: `${label}最小值 ${props.min}`,
        trigger: 'change',
      });
    }
    if (Number(props.maxlength) > -1) {
      rules.push({
        validator: (value) => defaultValidator.maxlength(value, props.maxlength as number),
        message: `${label}最大长度 ${props.maxlength}`,
        trigger: 'change',
      });
    }
    return rules;
  };

  const mergeRules: (configRules: IRule[], propRules: ReturnType<typeof getRulesFromProps>) => IFinalRule[] = (
    configRules,
    propRules,
  ) => {
    let customRequired = false;
    let customEmail = false;

    const formatConfigRules = configRules.reduce<IFinalRule[]>((result, rule) => {
      let rulevalidator: any;
      if (rule.required) {
        rulevalidator = isFunction(rule.validator) ? rule.validator : defaultValidator.required;
        customRequired = true;
      } else if (rule.email) {
        rulevalidator = isFunction(rule.validator) ? rule.validator : defaultValidator.email;
        customEmail = true;
      } else if (Number(rule.max) > -1) {
        rulevalidator = (value: any) => defaultValidator.max(value, rule.max as number);
      } else if (Number(rule.min) > -1) {
        rulevalidator = (value: any) => defaultValidator.min(value, rule.max as number);
      } else if (Number(rule.maxlength) > -1) {
        rulevalidator = (value: any) => defaultValidator.min(value, rule.max as number);
      } else if (Object.prototype.toString.call(rule.pattern) === '[object RegExp]') {
        rulevalidator = (value: any) => defaultValidator.pattern(value, rule.pattern as RegExp);
      } else if (isFunction(rule.validator)) {
        rulevalidator = rule.validator;
      } else {
        // 不支持的配置规则
        return result;
      }
      result.push({
        validator: rulevalidator,
        message: rule.message,
        trigger: rule.trigger || 'blur',
      });
      return result;
    }, []);

    // 自定义配置验证规则覆盖内置验证规则
    const filterPropRules = propRules.reduce<IFinalRule[]>((result, ruleItem) => {
      if (ruleItem.required && customRequired) {
        return result;
      }
      if (ruleItem.email && customEmail) {
        return result;
      }
      result.push(ruleItem);
      return result;
    }, []);

    return [...filterPropRules, ...formatConfigRules];
  };

  let registerRules: IRule[] = [];

  const rootRef = ref<HTMLElement>();
  const isRowspanRender = ref(false);
  const isFocused = ref(false);
  const isPreviousSiblingRowspan = ref(false);

  const validateState = reactive({
    isError: false,
    errorMessage: 'error',
  });

  const disabledTips = computed(() => {
    if (!props.disabledMethod) {
      return '';
    }
    const columnIndex = tableContext!.getColumnRelateRowIndexByInstance(currentInstance);

    const result = props.disabledMethod(tableContext!.props.model[columnIndex], props.field);
    if (typeof result === 'string') {
      return result;
    }
    return result ? '无法操作' : '';
  });

  const validate = (): Promise<boolean> => {
    if (!tableContext) {
      return Promise.resolve(false);
    }
    // 没有设置 field 不进行验证
    if (!props.field) {
      return Promise.resolve(true);
    }
    let rules: IRule[] = [];
    // 继承 form 的验证规则
    if (tableContext && tableContext.props.rules && hasOwn(tableContext.props.rules, props.field)) {
      rules = tableContext.props.rules[props.field];
    }
    // form-item 自己的 rules 规则优先级更高
    if (props.rules) {
      rules = props.rules as IRule[];
    }

    // 通过 useColumn 注册
    if (registerRules.length > 0) {
      rules = registerRules;
    }

    // 合并规则属性配置
    const finalRuleList = mergeRules(rules, getRulesFromProps(props));

    // 重新触发验证重置上次的验证状态
    if (rules.length > 0) {
      validateState.isError = false;
      validateState.errorMessage = '';
    }

    const value = get(tableContext.props.model, props.field);

    const doValidate = (() => {
      let stepIndex = -1;
      return (): Promise<boolean> => {
        stepIndex = stepIndex + 1;
        // 验证通过
        if (stepIndex >= finalRuleList.length) {
          tableContext.emits('validate', props.field || '', true, '');
          return Promise.resolve(true);
        }
        const rule = finalRuleList[stepIndex];

        return Promise.resolve().then(() => {
          const result = rule.validator(value);
          // 异步验证（validator 返回一个 Promise）
          if (typeof result !== 'boolean' && typeof result !== 'string' && typeof result.then === 'function') {
            return result
              .then((data) => {
                // 异步验证结果为 false
                if (data === false) {
                  return Promise.reject(getRuleMessage(rule));
                }
                if (typeof data === 'string') {
                  return Promise.reject(data);
                }
              })
              .then(
                () => doValidate(),
                (errorMessage: string) => {
                  validateState.isError = true;
                  validateState.errorMessage = errorMessage;
                  tableContext.emits('validate', props.field || '', false, errorMessage);
                  return Promise.reject(validateState.errorMessage);
                },
              );
          }
          // 同步验证失败
          if (result === false) {
            const errorMessage = getRuleMessage(rule);
            validateState.isError = true;
            // 验证结果返回的是 String 表示验证失败，返回结果作为错误信息
            validateState.errorMessage = typeof result === 'string' ? result : errorMessage;
            tableContext.emits('validate', props.field || '', false, errorMessage);
            return Promise.reject(validateState.errorMessage);
          }
          // 下一步
          return doValidate();
        });
      };
    })();
    return doValidate();
  };

  provide(EditableTableColumnKey, {
    blur: () => {
      isFocused.value = false;
    },
    focus: () => {
      isFocused.value = true;
    },
    registerRules: (rules: IRule[]) => {
      registerRules = rules;
    },
    validate,
    clearValidate: () => {
      validateState.isError = false;
      validateState.errorMessage = '';
    },
  });

  onMounted(() => {
    rowContext?.registerColumn({
      key: columnKey,
      instance: currentInstance,
      el: rootRef.value as HTMLElement,
      props,
      slots,
      validate,
    });

    // 判断rowspan 在当前 column生效状态
    const allColumnList = tableContext?.getAllColumnList() || [];
    let rowspanNum = 0;
    isRowspanRender.value = true;
    allColumnList.forEach((rowColumnList) => {
      rowColumnList.forEach((columnItem, columnIndex) => {
        if (columnItem.key === columnKey) {
          if (columnItem.props.rowspan && columnItem.props.rowspan > 1) {
            if (rowspanNum === 0) {
              rowspanNum = columnItem.props.rowspan;
            }
            rowspanNum = rowspanNum - 1;
            isRowspanRender.value = rowspanNum < 1;
          }
          if (columnIndex > 0) {
            isPreviousSiblingRowspan.value = Number(rowColumnList[columnIndex - 1]!.props.rowspan) > 1;
          }
        }
      });
    });
  });

  onBeforeUnmount(() => {
    rowContext?.unregisterColumn(columnKey);
    registerRules = [];
  });

  defineExpose<Expose>({
    validate,
  });
</script>
<style lang="less">
  .bk-editable-table {
    td.bk-editable-table-body-column {
      &.is-focused {
        z-index: 99;

        &::before {
          border-color: #3a84ff;
        }
      }

      &.is-disabled {
        .bk-editable-table-field-cell {
          &::after {
            position: absolute;
            z-index: 1;
            cursor: not-allowed;
            content: '';
            inset: 0;
          }
        }
      }

      &.is-error {
        z-index: 99;
        background: #fff1f1;

        &::before {
          border-color: #ea3636;
        }

        .bk-editable-table-field-cell {
          background: #fff1f1;
        }
      }

      &.is-previous-sibling-rowspan {
        &::before {
          left: -1px;
        }
      }
    }
  }

  .bk-editable-table-field-cell {
    position: relative;
    display: flex;
    height: 100%;
    min-height: 40px;
    align-items: center;
  }

  .bk-editable-table-column-error {
    position: absolute;
    top: 50%;
    right: 0;
    z-index: 9;
    display: flex;
    height: 40px;
    padding: 0 8px;
    color: #ea3636;
    align-items: center;
    transform: translateY(-50%);
  }
</style>
