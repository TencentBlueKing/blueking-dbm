<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <td
    v-if="isRowspanRender"
    :key="columnKey"
    ref="root"
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
      v-if="slots.tips"
      ref="tips"
      class="bk-editable-table-body-column-tips">
      <slot name="tips" />
    </div>
    <div
      v-if="validateState.isError"
      class="bk-editable-table-column-error">
      <slot
        name="error"
        v-bind="{ message: validateState.errorMessage }">
        <i
          v-bk-tooltips="errorTips"
          class="bk-dbm db-icon-exclamation-fill" />
      </slot>
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
    type Ref,
    type VNode,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getColumnCount, tableInjectKey } from './Index.vue';
  import { injectKey } from './Row.vue';
  import { type IRule } from './types';
  import defaultValidator from './validator';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    appendRules?: IRule[];
    description?: string;
    disabledMethod?: (rowData?: any, field?: string) => string | boolean;
    email?: boolean;
    field?: string;
    fixed?: 'left' | 'right';
    idMark?: string; // 作为身份标记，不参入任何内部逻辑处理，
    label: string;
    loading?: boolean;
    max?: number;
    maxlength?: number;
    maxWidth?: number;
    min?: number;
    minWidth?: number;
    readonly?: boolean;
    required?: boolean;
    resizeable?: boolean;
    rowspan?: number;
    rules?: IRule[];
    width?: number;
  }

  export type Emits = (e: 'validate', result: boolean, message: string) => boolean;

  interface Slots {
    default: () => VNode;
    error?: (params: { message: string }) => VNode;
    head?: () => VNode;
    headAppend?: () => VNode;
    headPrepend?: () => VNode;
    tips?: () => VNode;
  }

  interface Expose {
    clearValidate: () => void;
    getRowIndex: () => number;
    validate: () => Promise<boolean>;
    viewError: (message: string, idMark: string) => void;
  }

  export interface IContext {
    clearValidate: () => void;
    el: HTMLElement;
    instance: ComponentInternalInstance;
    isRowspanRender: Ref<boolean>;
    key: string;
    props: Props;
    slots: Slots;
    uniqueKey: string;
    validate: (trigger?: string) => Promise<boolean>;
  }

  export const EditableTableColumnKey: InjectionKey<{
    blur: () => void;
    clearValidate: () => void;
    focus: () => void;
    getRowIndex: () => number;
    registerRules: (params: IRule[]) => void;
    validate: (trigger?: string) => Promise<boolean>;
  }> = Symbol('EditableTableColumnKey');
</script>
<script setup lang="ts">
  const props = withDefaults(defineProps<Props>(), {
    appendRules: undefined,
    description: undefined,
    disabledMethod: undefined,
    field: undefined,
    fixed: undefined,
    idMark: undefined,
    max: undefined,
    maxlength: undefined,
    maxWidth: undefined,
    min: undefined,
    minWidth: undefined,
    readonly: false,
    resizeable: true,
    rowspan: undefined,
    rules: undefined,
    width: undefined,
  });
  const emits = defineEmits<Emits>();
  const slots = defineSlots<Slots>();

  const { t } = useI18n();

  const tableContext = inject(tableInjectKey);
  const rowContext = inject(injectKey);
  const currentInstance = getCurrentInstance() as ComponentInternalInstance;

  const getRowIndex = () => tableContext!.getColumnRelateRowIndexByInstance(currentInstance);

  const uniqueKey = `${Date.now()}#${getColumnCount()}`;
  const columnKey = `bk-editable-table-column-${rowContext?.getColumnIndex()}`;

  interface IFinalRule {
    message: string | (() => string);
    trigger: string;
    validator: (value: any, rowDataValue?: Record<string, any>) => Promise<boolean | string> | boolean | string;
  }

  let loadingValidatorTimer: ReturnType<typeof setTimeout>;

  const getRulesFromProps = (props: Props) => {
    const rules: ({
      email?: boolean;
      required?: boolean;
    } & IFinalRule)[] = [];

    const label = props.label || '';
    if (props.loading) {
      rules.push({
        message: t('{n}查询中', { n: label }),
        trigger: '',
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
      });
    }
    if (props.required) {
      rules.push({
        message: t('{n}不能为空', { n: label }),
        required: true,
        trigger: 'change',
        validator: defaultValidator.required,
      });
    }
    if (props.email) {
      rules.push({
        email: true,
        message: t('{n}不是 email', { n: label }),
        trigger: 'change',
        validator: (value: string) => defaultValidator.email(value),
      });
    }
    if (props.max !== undefined) {
      rules.push({
        message: t('{n}最大值 {max}', { max: props.max, n: label }),
        trigger: 'change',
        validator: (value: number) => defaultValidator.max(value, props.max as number),
      });
    }
    if (props.min !== undefined) {
      rules.push({
        message: t('{n}最小值 {min}', { min: props.min, n: label }),
        trigger: 'change',
        validator: (value) => defaultValidator.min(value, props.min as number),
      });
    }
    if (props.maxlength !== undefined) {
      rules.push({
        message: t('{n}最大长度 {maxlength}', { maxlength: props.maxlength, n: label }),
        trigger: 'change',
        validator: (value) => defaultValidator.maxlength(value, props.maxlength as number),
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
      } else if (rule.max !== undefined) {
        rulevalidator = (value: any) => defaultValidator.max(value, rule.max as number);
      } else if (rule.min !== undefined) {
        rulevalidator = (value: any) => defaultValidator.min(value, rule.min as number);
      } else if (rule.maxlength !== undefined) {
        rulevalidator = (value: any) => defaultValidator.maxlength(value, rule.maxlength as number);
      } else if (Object.prototype.toString.call(rule.pattern) === '[object RegExp]') {
        rulevalidator = (value: any) => defaultValidator.pattern(value, rule.pattern as RegExp);
      } else if (_.isFunction(rule.validator)) {
        rulevalidator = rule.validator;
      } else {
        // 不支持的配置规则
        return result;
      }
      result.push({
        message: rule.message,
        trigger: rule.trigger || 'blur',
        validator: rulevalidator,
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

  const rootRef = useTemplateRef<HTMLElement>('root');
  const tipsRef = useTemplateRef<HTMLElement>('tips');
  const isRowspanRender = ref(false);
  const isFocused = ref(false);
  const isPreviousSiblingRowspan = ref(false);

  const validateState = reactive({
    errorMessage: 'error',
    isError: false,
  });

  const disabledTips = computed(() => {
    if (!props.disabledMethod) {
      return '';
    }
    const rowIndex = rowContext!.getRowIndex();

    const result = props.disabledMethod(tableContext!.props.model[rowIndex], props.field);
    if (typeof result === 'string') {
      return result;
    }
    return result ? t('无法操作') : '';
  });

  // tooltips 内容以 innerHTML 渲染，错误信息可能来自接口返回，需要转义
  const errorTips = computed(() => _.escape(validateState.errorMessage));

  const calcRowspanRender = (rowspanNumMap: Map<string, number>) => {
    // 判断rowspan 在当前 column生效状态
    const allColumnList = tableContext?.getAllColumnList() || [];
    for (const rowColumnList of allColumnList) {
      const columnIndex = _.findIndex(rowColumnList, (columnItem) => columnItem.uniqueKey === uniqueKey);
      if (columnIndex < 0) {
        continue;
      }
      const columnItem = rowColumnList[columnIndex]!;
      if (columnItem.props.rowspan && columnItem.props.rowspan > 0) {
        const rowspanNum = rowspanNumMap.get(columnKey);
        // 计数为 0 表示上一组合并已经结束，当前单元格作为新一组的起点渲染
        if (!rowspanNum) {
          isRowspanRender.value = true;
          rowspanNumMap.set(columnKey, -columnItem.props.rowspan + 1);
        } else {
          isRowspanRender.value = false;
          rowspanNumMap.set(columnKey, rowspanNum + 1);
        }
      } else {
        isRowspanRender.value = true;
      }

      // 同行的前一列被合并（不渲染）时，当前单元格需要左移 1px 与前一列的边框重叠
      if (columnIndex > 0) {
        isPreviousSiblingRowspan.value = !rowColumnList[columnIndex - 1]!.isRowspanRender.value;
      }
      return;
    }
  };

  watch(
    () => [tableContext?.props.model, props.rowspan],
    () => {
      setTimeout(() => {
        tableContext?.runRowspanTask();
      });
    },
  );

  watch(
    isRowspanRender,
    () => {
      nextTick(() => {
        if (isRowspanRender.value) {
          // eslint-disable-next-line no-underscore-dangle
          (rootRef.value as any).__getCurrentInstance__ = () => currentInstance;
        }
      });
    },
    {
      immediate: true,
    },
  );

  let tippyIns: Instance;

  const initTipsPopover = () => {
    if (!slots.tips) {
      return;
    }

    const tippyTarget = rootRef.value;

    if (tippyTarget) {
      tippyIns = tippy(tippyTarget as SingleTarget, {
        appendTo: () => document.body,
        arrow: true,
        content: tipsRef.value as HTMLElement,
        hideOnClick: false,
        interactive: true,
        maxWidth: 'none',
        offset: [0, 12],
        placement: 'top',
        popperOptions: {
          modifiers: [
            {
              name: 'flip',
              options: {
                allowedAutoPlacements: ['top-start', 'top-end'],
                fallbackPlacements: ['top', 'bottom'],
              },
            },
          ],
          strategy: 'fixed',
        },
        theme: 'light db-popconfirm-theme',
        trigger: 'manual',
        zIndex: 9999,
      });
    }
  };

  const clearValidate = () => {
    validateState.isError = false;
    validateState.errorMessage = '';
  };

  interface IValidateDeferred {
    promise: Promise<boolean>;
    reject: (result: boolean) => void;
    resolve: (result: boolean) => void;
    timer?: ReturnType<typeof setTimeout>;
  }

  // 没有 trigger 表示整表验证
  const fullValidateTriggerKey = '';
  const validateDeferredMap: Record<string, IValidateDeferred | undefined> = {};

  const runValidate = (trigger?: string): Promise<boolean> => {
    if (!tableContext) {
      return Promise.resolve(false);
    }
    const field = props.field || '';
    let rules: IRule[] = [];
    // 继承 table 的验证规则
    if (tableContext.props.rules && _.has(tableContext.props.rules, field)) {
      rules = tableContext.props.rules[field]!;
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

    // 合并规则属性配置
    const finalRuleList = getTriggerRules(mergeRules(rules, getRulesFromProps(props)), trigger);

    if (finalRuleList.length > 0) {
      // 重新触发验证重置上次的验证状态
      validateState.isError = false;
      validateState.errorMessage = '';
    }

    const rowIndex = rowContext!.getRowIndex();
    const rowDataValue = {
      rowData: tableContext.props.model[rowIndex]!,
      rowIndex,
    };
    const value = _.get(rowDataValue.rowData, field || '_');

    const setValidateError = (errorMessage: string) => {
      validateState.isError = true;
      validateState.errorMessage = errorMessage;
      emits('validate', false, errorMessage);
      tableContext.emits('validate', field, false, errorMessage);
      return Promise.reject(false);
    };

    const doValidate = (stepIndex: number): Promise<boolean> => {
      // 验证通过
      if (stepIndex >= finalRuleList.length) {
        emits('validate', true, '');
        tableContext.emits('validate', field, true, '');
        return Promise.resolve(true);
      }
      const rule = finalRuleList[stepIndex]!;

      return Promise.resolve()
        .then(() => rule.validator(value, rowDataValue))
        .then(
          (result) => {
            // 只有 false 和字符串表示验证不通过
            if (result === false) {
              return setValidateError(getRuleMessage(rule));
            }
            if (typeof result === 'string') {
              return setValidateError(result);
            }
            return doValidate(stepIndex + 1);
          },
          (errorMessage: string) => setValidateError(errorMessage),
        );
    };

    return doValidate(0);
  };

  // 与 DbForm 的验证协议保持一致：验证不通过 reject(false)，通过 resolve(true)
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

    const triggerKey = trigger ?? fullValidateTriggerKey;
    const delay = Math.max(Number(tableContext.props.validateDelay || 60), 60);

    const startTimer = (deferred: IValidateDeferred) =>
      setTimeout(() => {
        // 整表验证排队时以整表验证的结果为准，避免局部验证覆盖整表验证的错误状态
        const fullValidateDeferred =
          triggerKey === fullValidateTriggerKey ? undefined : validateDeferredMap[fullValidateTriggerKey];

        validateDeferredMap[triggerKey] = undefined;

        // setTimeout 延迟执行 Column 可能会已经被卸载，已卸载的单元格不阻塞验证
        if (!currentInstance.isMounted) {
          deferred.resolve(true);
          return;
        }
        if (fullValidateDeferred) {
          fullValidateDeferred.promise.then(deferred.resolve, deferred.reject);
          return;
        }
        runValidate(trigger).then(deferred.resolve, deferred.reject);
      }, delay);

    // 延迟窗口内同一触发器的重复调用共享同一次验证结果
    const pendingDeferred = validateDeferredMap[triggerKey];
    if (pendingDeferred) {
      clearTimeout(pendingDeferred.timer);
      pendingDeferred.timer = startTimer(pendingDeferred);
      return pendingDeferred.promise;
    }

    let resolveValidate!: IValidateDeferred['resolve'];
    let rejectValidate!: IValidateDeferred['reject'];
    const promise = new Promise<boolean>((resolve, reject) => {
      resolveValidate = resolve;
      rejectValidate = reject;
    });
    const deferred: IValidateDeferred = {
      promise,
      reject: rejectValidate,
      resolve: resolveValidate,
    };
    validateDeferredMap[triggerKey] = deferred;
    deferred.timer = startTimer(deferred);

    return deferred.promise;
  };

  const viewError = (message: string, idMark: string) => {
    if (props.idMark && idMark === props.idMark) {
      validateState.isError = Boolean(message);
      validateState.errorMessage = message;
    }
  };

  provide(EditableTableColumnKey, {
    blur: () => {
      isFocused.value = false;
      tippyIns?.hide();
    },
    clearValidate,
    focus: () => {
      isFocused.value = true;
      tippyIns?.show();
    },
    getRowIndex,
    registerRules: (rules: IRule[]) => {
      registerRules = rules;
    },
    validate,
  });

  onMounted(() => {
    rowContext?.registerColumn({
      clearValidate,
      el: rootRef.value as HTMLElement,
      instance: currentInstance,
      isRowspanRender,
      key: columnKey,
      props,
      slots,
      uniqueKey,
      validate,
    });

    // setTimeout 确保 registerColumn 结束
    setTimeout(() => {
      tableContext?.pushRowspanTask({
        getRowIndex,
        run: calcRowspanRender,
      });
      tableContext?.runRowspanTask();
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
    tableContext?.removeRowspanTask(calcRowspanRender);
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  });

  defineExpose<Expose>({
    clearValidate,
    getRowIndex,
    validate,
    viewError,
  });
</script>
<style lang="less">
  @keyframes editable-table-column-loading {
    0% {
      transform: rotateZ(0);
    }

    100% {
      transform: rotateZ(360deg);
    }
  }

  .bk-editable-table-body-column {
    --column-hover-z-index: 101;
    --column-focus-z-index: 102;
    --column-error-z-index: 100;
    --column-fixed-z-index: 111;
    --column-fixed-hover-z-index: 112;
    --column-fixed-focus-z-index: 122;
    --column-fixed-error-z-index: 121;
    --column-hover-border-color: #a3c5fd;
    --column-focus-border-color: #3a84ff;
    --column-error-border-color: #ea3636;
    --column-readonly-border-color: #dcdee5;
    --column-error-background-color: #fff1f1;
    --column-readonly-background-color: #fafbfd;
    --column-disabled-background-color: #fafbfd;

    &.is-disabled {
      background: var(--column-disabled-background-color);

      .bk-editable-table-field-cell {
        > *:not(.bk-editable-table-column-disabled-mask) {
          position: relative;
          z-index: 0;
          background: var(--column-disabled-background-color);
        }

        *:not(.bk-editable-table-column-disabled-mask) {
          pointer-events: none;
          cursor: not-allowed;
        }
      }
    }

    &.is-readonly {
      background: var(--column-readonly-background-color);

      &::before {
        border-color: var(--column-readonly-border-color);
      }

      .bk-editable-table-field-cell {
        & > * {
          background: var(--column-readonly-background-color);
        }

        * {
          pointer-events: none;
        }
      }
    }

    &:hover {
      z-index: var(--column-hover-z-index);

      &::before {
        border-color: var(--column-hover-border-color);
      }
    }

    &.is-focused {
      z-index: var(--column-focus-z-index);

      &::before {
        border-color: var(--column-focus-border-color);
      }
    }

    &.is-error {
      z-index: var(--column-error-z-index);
      background: var(--column-error-background-color);

      &::before {
        border-color: var(--column-error-border-color);
      }

      .bk-editable-table-field-cell {
        padding-right: 20px;

        & > * {
          background: var(--column-error-background-color);
        }
      }
    }

    &.is-previous-sibling-rowspan {
      &::before {
        left: -1px;
      }
    }

    &.is-fixed {
      z-index: var(--column-fixed-z-index);

      &.is-error {
        z-index: var(--column-fixed-error-z-index);
      }

      &.is-focused {
        z-index: var(--column-fixed-focus-z-index);
      }

      &:hover {
        z-index: var(--column-fixed-hover-z-index);
      }
    }
  }

  .bk-editable-table-field-cell {
    position: relative;
    display: flex;
    min-height: 40px;
    font-size: 12px;
    line-height: 20px;
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
    font-size: 14px;
    color: #ea3636;
    transform: translateY(-50%);
    align-items: center;
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
