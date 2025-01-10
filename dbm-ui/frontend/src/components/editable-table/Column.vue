<template>
  <td
    v-if="isRowspanRender"
    ref="rootRef"
    class="bk-editable-table-body-column"
    :class="{
      [`fixed-${fixed}-column`]: fixed,
      'is-focused': isFocused,
      'is-error': validateState.isError,
      'is-readonly': readonly,
      'is-disabled': Boolean(disabledTips),
      'is-previous-sibling-rowspan': isPreviousSiblingRowspan,
      'is-fixed':
        (fixed === 'left' && tableContext?.fixedLeft.value) || (fixed === 'right' && tableContext?.fixedRight.value),
    }"
    :data-name="columnKey"
    :rowspan="rowspan">
    <div
      v-bk-tooltips="{
        content: disabledTips,
        disabled: !disabledTips,
      }"
      class="bk-editable-table-field-cell"
      :style="{
        width: `${tableContext?.columnSizeConfig.value[columnKey]?.renderWidth}px`,
      }">
      <slot />
      <div
        v-if="loading"
        class="bk-editable-table-column-loading">
        <div class="loading-flag">
          <Loading />
        </div>
      </div>
      <div
        v-if="Boolean(disabledTips)"
        class="bk-editable-table-column-disabled-mask" />
    </div>
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
    <div
      v-if="slots.tips"
      ref="tipsRef"
      class="bk-editable-table-body-column-tips">
      <slot name="tips" />
    </div>
  </td>
</template>
<script lang="ts">
  import { Loading } from 'bkui-vue/lib/icon';
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
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
    loading?: boolean;
    appendRules?: IRule[];
    readonly?: boolean;
    resizeable?: boolean;
  }

  interface Slots {
    default: () => VNode;
    head?: () => VNode;
    headPrepend?: () => VNode;
    headAppend?: () => VNode;
    error?: (params: { message: string }) => VNode;
    tips?: () => VNode;
  }

  interface Expose {
    validate: () => Promise<boolean>;
    clearValidate: () => void;
    getRowIndex: () => number;
  }

  export interface IContext {
    instance: ComponentInternalInstance;
    el: HTMLElement;
    key: string;
    props: Props;
    slots: Slots;
    validate: (trigger?: string) => Promise<boolean>;
  }

  // eslint-disable-next-line @typescript-eslint/naming-convention
  export const EditableTableColumnKey: InjectionKey<{
    blur: () => void;
    focus: () => void;
    registerRules: (params: IRule[]) => void;
    validate: (trigger?: string) => Promise<boolean>;
    clearValidate: () => void;
    getRowIndex: () => number;
  }> = Symbol('EditableTableColumnKey');
</script>
<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    field: undefined,
    rowspan: undefined,
    width: undefined,
    minWidth: undefined,
    maxWidth: undefined,
    rules: undefined,
    max: undefined,
    min: undefined,
    maxlength: undefined,
    fixed: undefined,
    disabledMethod: undefined,
    description: undefined,
    appendRules: undefined,
    readonly: false,
    resizeable: true,
  });
  const slots = defineSlots<Slots>();

  const tableContext = inject(tableInjectKey);
  const rowContext = inject(injectKey);
  const currentInstance = getCurrentInstance() as ComponentInternalInstance;

  const columnKey = `bk-editable-table-column-${rowContext?.getColumnIndex()}`;

  interface IFinalRule {
    validator: (value: any, rowData?: Record<string, any>) => Promise<boolean | string> | boolean | string;
    message: string | (() => string);
    trigger: string;
  }

  let loadingValidatorTimer: ReturnType<typeof setTimeout>;

  const getRulesFromProps = (props: Props) => {
    const rules: (IFinalRule & {
      required?: boolean;
      email?: boolean;
    })[] = [];

    const label = props.label || '';
    if (props.loading) {
      rules.push({
        validator: () => {
          clearTimeout(loadingValidatorTimer);
          return new Promise((resolve) => {
            const loop = () => {
              if (!props.loading) {
                resolve(true);
                return;
              }
              loadingValidatorTimer = setTimeout(() => {
                loop();
              }, 500);
            };
            loop();
          });
        },
        message: `${label}查询中`,
        trigger: '',
      });
    }
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
        rulevalidator = _.isFunction(rule.validator) ? rule.validator : defaultValidator.required;
        customRequired = true;
      } else if (rule.email) {
        rulevalidator = _.isFunction(rule.validator) ? rule.validator : defaultValidator.email;
        customEmail = true;
      } else if (Number(rule.max) > -1) {
        rulevalidator = (value: any) => defaultValidator.max(value, rule.max as number);
      } else if (Number(rule.min) > -1) {
        rulevalidator = (value: any) => defaultValidator.min(value, rule.max as number);
      } else if (Number(rule.maxlength) > -1) {
        rulevalidator = (value: any) => defaultValidator.min(value, rule.max as number);
      } else if (Object.prototype.toString.call(rule.pattern) === '[object RegExp]') {
        rulevalidator = (value: any) => defaultValidator.pattern(value, rule.pattern as RegExp);
      } else if (_.isFunction(rule.validator)) {
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

  const getTriggerRules = (rules: IFinalRule[], trigger?: string) =>
    rules.reduce((result, rule) => {
      if (!rule.trigger || !trigger) {
        result.push(rule);
        return result;
      }
      if (rule.trigger === trigger) {
        result.push(rule);
      }
      return result;
    }, [] as IFinalRule[]);

  const getRuleMessage = (rule: IFinalRule) => {
    if (typeof rule.message === 'function') {
      return rule.message();
    }
    return rule.message;
  };

  let registerRules: IRule[] = [];

  const rootRef = ref<HTMLElement>();
  const tipsRef = ref<HTMLElement>();
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

  let tippyIns: Instance;

  const initTipsPopover = () => {
    if (!slots.tips) {
      return;
    }

    const tippyTarget = rootRef.value;

    if (tippyTarget) {
      tippyIns = tippy(tippyTarget as SingleTarget, {
        content: tipsRef.value,
        placement: 'top',
        appendTo: () => document.body,
        theme: 'light db-popconfirm-theme',
        maxWidth: 'none',
        trigger: 'manual',
        interactive: true,
        arrow: true,
        offset: [0, 12],
        zIndex: 9999,
        hideOnClick: false,
        popperOptions: {
          strategy: 'fixed',
          modifiers: [
            {
              name: 'flip',
              options: {
                fallbackPlacements: ['top', 'bottom'],
                allowedAutoPlacements: ['top-start', 'top-end'],
              },
            },
          ],
        },
      });
    }
  };

  const getRowIndex = () => tableContext!.getColumnRelateRowIndexByInstance(currentInstance);
  const clearValidate = () => {
    validateState.isError = false;
    validateState.errorMessage = '';
  };

  const triggerChangeQueue: string[] = [];
  const triggerBlurQueue: string[] = [];
  const triggerQueue: undefined[] = [];
  const validate = (trigger?: string): Promise<boolean> => {
    if (!tableContext) {
      return Promise.resolve(false);
    }
    // 单元格被合并跳过验证
    if (!isRowspanRender.value) {
      return Promise.resolve(true);
    }
    // 没有设置 field 不进行验证
    if (!props.field) {
      return Promise.resolve(true);
    }
    let rules: IRule[] = [];
    // 继承 table 的验证规则
    if (tableContext?.props.rules && _.has(tableContext.props.rules, props.field)) {
      rules = tableContext.props.rules[props.field];
    }
    // column 自己的 rules 规则优先级更高
    if (props.rules) {
      rules = props.rules as IRule[];
    } else if (props.appendRules) {
      // 配置了 props.rules 时 props.appendRules 不生效
      // props.appendRules 与 table 的验证规则合并且优先级高
      rules = [...rules, ...props.appendRules];
    }

    // 通过 useColumn 注册
    if (registerRules.length > 0) {
      rules = registerRules;
    }

    const doValidate = (() => {
      let stepIndex = -1;
      return (finalRuleList: IFinalRule[], value: any, rowDataValue: Record<string, any>): Promise<boolean> => {
        stepIndex = stepIndex + 1;
        // 验证通过
        if (stepIndex >= finalRuleList.length) {
          tableContext.emits('validate', props.field || '', true, '');
          return Promise.resolve(true);
        }
        const rule = finalRuleList[stepIndex];

        return Promise.resolve().then(() => {
          const result = rule.validator(value, rowDataValue);
          // 同步验证通过下一步
          if (result === true) {
            return doValidate(finalRuleList, value, rowDataValue);
          }
          // Promise异步处理验证结果
          return Promise.resolve(result)
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
              () => doValidate(finalRuleList, value, rowDataValue),
              (errorMessage: string) => {
                validateState.isError = true;
                validateState.errorMessage = errorMessage;
                tableContext.emits('validate', props.field || '', false, errorMessage);
                return Promise.reject(validateState.errorMessage);
              },
            );
        });
      };
    })();

    if (trigger !== undefined) {
      if (trigger === 'change') {
        triggerChangeQueue.push(trigger);
      } else if (trigger === 'blur') {
        triggerBlurQueue.push(trigger);
      }
    } else {
      triggerQueue.push(trigger);
    }

    return new Promise((resolve, reject) => {
      const delay = Math.max(Number(tableContext.props.validateDelay || 60), 60);
      setTimeout(() => {
        // setTimeout 延迟执行 Column 可能会已经被卸载
        if (!currentInstance.isMounted) {
          return reject(false);
        }
        if (trigger === undefined) {
          triggerQueue.pop();
          if (triggerQueue.length > 0) {
            return reject(false);
          }
        }

        // 处理 change 和 blur 触发器
        if (trigger === 'change' || trigger === 'blur') {
          const latestQueue = trigger === 'change' ? triggerChangeQueue : triggerBlurQueue;
          latestQueue.pop();
          if (triggerQueue.length > 0 || latestQueue.length > 0) {
            return reject(false);
          }
        }

        // 合并规则属性配置
        const finalRuleList = getTriggerRules(mergeRules(rules, getRulesFromProps(props)), trigger);

        if (finalRuleList.length > 0) {
          // 重新触发验证重置上次的验证状态
          validateState.isError = false;
          validateState.errorMessage = '';
        }

        const rowDataValue = tableContext.props.model[rowContext!.getRowIndex()];
        const value = _.get(rowDataValue, props.field || '_');

        doValidate(finalRuleList, value, rowDataValue).then(
          () => {
            resolve(true);
          },
          () => {
            reject(false);
          },
        );
      }, delay);
    });
  };

  provide(EditableTableColumnKey, {
    blur: () => {
      isFocused.value = false;
      tippyIns?.hide();
    },
    focus: () => {
      isFocused.value = true;
      tippyIns?.show();
    },
    registerRules: (rules: IRule[]) => {
      registerRules = rules;
    },
    validate,
    clearValidate,
    getRowIndex,
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

    // 初始化 tips 弹框
    setTimeout(() => {
      initTipsPopover();
    });
  });

  onBeforeUnmount(() => {
    rowContext?.unregisterColumn(columnKey);
    registerRules = [];
    clearTimeout(loadingValidatorTimer);
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  });

  defineExpose<Expose>({
    validate,
    clearValidate,
    getRowIndex,
  });
</script>
<style lang="less">
  @hover-z-index: 100;
  @focus-z-index: 102;
  @fixed-focus-z-index: 122;
  @error-z-index: 101;
  @fixed-error-z-index: 121;

  @keyframes editable-table-column-loading {
    0% {
      transform: rotateZ(0);
    }

    100% {
      transform: rotateZ(360deg);
    }
  }

  .bk-editable-table-body-column {
    &:hover {
      z-index: @hover-z-index;

      &::before {
        border-color: #979ba5;
      }
    }

    &.is-disabled {
      .bk-editable-table-field-cell {
        background: #fafbfd;

        & > *:not(.bk-editable-table-column-disabled-mask) {
          pointer-events: none;
        }
      }
    }

    &.is-error {
      z-index: @error-z-index;
      background: #fff1f1;

      &::before {
        border-color: #ea3636;
      }

      .bk-editable-table-field-cell {
        padding-right: 20px;
        background: #fff1f1;
      }
    }

    &.is-focused {
      z-index: @focus-z-index;

      &::before {
        border-color: #3a84ff;
      }
    }

    &.is-readonly {
      &::before {
        border-color: #dcdee5;
      }
    }

    &.is-previous-sibling-rowspan {
      &::before {
        left: -1px;
      }
    }

    &.is-fixed {
      &.is-error {
        z-index: @fixed-error-z-index;
      }

      &.is-focused {
        z-index: @fixed-focus-z-index;
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
    padding-right: 8px;
    color: #ea3636;
    align-items: center;
    transform: translateY(-50%);
  }

  .bk-editable-table-column-loading {
    position: absolute;
    z-index: 1;
    display: flex;
    inset: 0;
    align-items: center;
    justify-content: center;
    background-color: rgb(255 255 255 / 90%);

    .loading-flag {
      width: 16px;
      height: 16px;
      font-size: 16px;
      color: #3a84ff;
      animation: editable-table-column-loading 1.5s linear infinite;
    }
  }

  .bk-editable-table-column-disabled-mask {
    position: absolute;
    z-index: 1;
    cursor: not-allowed;
    content: '';
    inset: 0;
  }

  .bk-editable-table-body-column-tips {
    display: flex;
    padding: 3px 7px;
    font-size: 12px;
    line-height: 24px;
    flex-direction: column;
  }
</style>
