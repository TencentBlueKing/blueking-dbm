<template>
  <div class="bk-quick-search-value-panel">
    <ElConfigProvider :locale="zhCn">
      <component
        :is="renderCom"
        :config="config"
        v-bind="renderComProps"
        :model-value="modelValue"
        @change="handleChange" />
    </ElConfigProvider>
    <div
      v-if="isNeedComfirmAndReset || isSupportQuickSelect"
      class="bk-quick-search-panel-footer">
      <div class="bk-quick-search-panel-submit-tips">
        <template v-if="isSupportQuickSelect">
          <div class="action-tips">
            <div class="tag">
              <DbIcon type="up-big" />
            </div>
            <div class="tag">
              <DbIcon type="down-big" />
            </div>
            <span>移动光标</span>
          </div>
          <div class="action-tips">
            <div class="tag">Enter</div>
            <span>选中</span>
          </div>
        </template>
        <div
          v-if="isNeedComfirmAndReset"
          class="action-tips">
          <div
            v-if="isMacOs"
            class="tag">
            Cmd + Enter
          </div>
          <div
            v-else
            class="tag">
            Ctrl + Enter
          </div>
          <span>确定</span>
        </div>
      </div>
      <template v-if="isNeedComfirmAndReset">
        <Button
          size="small"
          style="margin-right: 8px; margin-left: 24px"
          variant="outline"
          @click="handleReset">
          重置
        </Button>
        <Button
          size="small"
          @click="handleConfirm">
          确定
        </Button>
      </template>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ElConfigProvider } from 'element-plus';
  import zhCn from 'element-plus/es/locale/lang/zh-cn';
  import { Button } from 'tdesign-vue-next';
  import { computed, onMounted } from 'vue';

  import { comType } from '@components/db-quick-search/bk-quick-search/constants';
  import type { IValue, Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

  import 'element-plus/dist/index.css';

  import Cascader from './components/Cascader.vue';
  import Custom from './components/Custom';
  import DatePicker from './components/DatePicker.vue';
  import DateRangePicker from './components/DateRangePicker.vue';
  import DatetimePicker from './components/DatetimePicker.vue';
  import DatetimeRangePciker from './components/DatetimeRangePciker.vue';
  import MultCascader from './components/MultCascader.vue';
  import MultSelect from './components/MultSelect.vue';
  import Select from './components/Select.vue';

  interface Props {
    config?: ContextProps['data'][number];
  }

  type Emits = (e: 'change', value: IValue['values']) => void;

  const props = withDefaults(defineProps<Props>(), {
    config: undefined,
  });
  const emits = defineEmits<Emits>();

  // modelValue 类型支持所有值，由各个组件自行处理
  const modelValue = defineModel<any[]>();

  const isMacOs = /Mac OS X ([\d_]+)/.test(navigator.userAgent);

  const renderCom = computed(() => {
    if (
      !props.config ||
      !props.config.type ||
      props.config.type === comType.INPUT ||
      props.config.type === comType.MULTIPLE_INPUT
    ) {
      return null;
    }

    const defaultComMap = {
      [comType.CASCADER]: Cascader,
      [comType.DATE]: DatePicker,
      [comType.DATE_RANGE]: DateRangePicker,
      [comType.DATETIME]: DatetimePicker,
      [comType.DATETIME_RANGE]: DatetimeRangePciker,
      [comType.MULTIPLE]: MultSelect,
      [comType.MULTIPLE_CASCADER]: MultCascader,
      [comType.SINGLE]: Select,
    } as const;

    if (defaultComMap[props.config.type]) {
      return defaultComMap[props.config.type];
    }
    if (props.config.component) {
      return Custom;
    }
    return null;
  });

  const renderComProps = computed(() => {
    if (!props.config) {
      return {};
    }
    console.log('renderComProps = ', props.config);
    return {
      list: props.config.list || [],
      ...Object.assign({}, props.config.props || {}),
    };
  });

  const isSupportQuickSelect = computed(() => {
    if (!props.config || !props.config.type) {
      return false;
    }
    return [comType.MULTIPLE, comType.SINGLE].includes(props.config.type as comType);
  });
  const isNeedComfirmAndReset = computed(() => {
    if (!props.config) {
      return false;
    }
    return props.config.type
      ? [comType.DATETIME, comType.DATETIME_RANGE, comType.MULTIPLE, comType.MULTIPLE_CASCADER].includes(
          props.config.type as comType,
        )
      : Boolean(props.config.showConfirmAndReset);
  });

  const handleChange = (value: IValue['values']) => {
    modelValue.value = value;
    if (isNeedComfirmAndReset.value) {
      return;
    }
    emits('change', value);
  };

  const handleReset = () => {
    modelValue.value = [];
  };

  const handleConfirm = () => {
    emits('change', modelValue.value || []);
  };

  onMounted(() => {
    const handleQuickConfigm = (event: KeyboardEvent) => {
      if (!isNeedComfirmAndReset.value) {
        return;
      }

      if (event.code === 'Enter') {
        if ((isMacOs && event.metaKey) || (!isMacOs && event.ctrlKey)) {
          handleConfirm();
        }
      }
    };
    document.body.addEventListener('keydown', handleQuickConfigm);
    onBeforeUnmount(() => {
      document.body.removeEventListener('keydown', handleQuickConfigm);
    });
  });
</script>
<style lang="less">
  .bk-quick-search-value-panel {
    --td-brand-color: #3f87ff;
    --td-brand-color-hover: #5594fa;
    --el-datepicker-active-color: #3f87ff;
    --el-datepicker-hover-text-color: #3f87ff;
    --el-color-primary: #3f87ff;

    padding: 0;
    font-size: 12px;

    .el-date-picker,
    .el-date-range-picker__time-picker-wrap {
      .el-time-panel {
        right: 0;
        left: unset;
      }
    }

    .value-item {
      display: flex;
      height: 32px;
      padding: 0 16px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      pointer-events: auto;
      cursor: pointer;
      transition: all 0.1s;
      flex: 1 0 32px;
      align-items: center;
      justify-content: flex-start;

      &:hover {
        color: #3a84ff;
        background-color: #eaf3ff;
      }

      &.active {
        color: #3a84ff;
        background: #f4f6fa;
      }
    }
  }

  .bk-quick-search-value-panel-filter-box {
    padding: 8px 12px 0;

    .t-input {
      border: none;
      border-bottom: 1px solid #eaebf0;
      border-radius: 0;
      box-shadow: none;

      &.t-input--focused {
        border-color: var(--td-brand-color);
      }
    }
  }

  .bk-quick-search-value-wrapper {
    max-height: 280px;
    min-width: 230px;
    min-height: 32px;
    margin-top: 8px;
    overflow: auto;
    font-size: 12px;
    pointer-events: all;
  }

  .bk-quick-search-value-panel-filter-empty {
    padding: 8px 16px;
    margin-top: -30px;
    color: #63656e;
    text-align: center;
    flex: 1;
  }
</style>
