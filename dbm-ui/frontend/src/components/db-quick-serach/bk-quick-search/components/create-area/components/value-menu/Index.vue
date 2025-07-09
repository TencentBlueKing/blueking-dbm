<template>
  <div class="bk-quick-search-type-menu">
    <component
      :is="renderCom"
      :config="config"
      :keyword="keyword"
      v-bind="renderComProps"
      :model-value="modelValue"
      @change="handleChange" />
    <div
      v-if="isRemoteList && (isRemoteListLoading || remoteList.length < 1)"
      style="padding: 0 16px; line-height: 32px; color: #63656e; text-align: center">
      {{ isRemoteListLoading ? '加载中...' : '暂无数据' }}
    </div>
    <div
      v-if="isNeedComfirmAndReset"
      class="bk-quick-search-type-menu-footer">
      <Button
        size="small"
        style="margin-right: 8px"
        variant="outline"
        @click="handleReset">
        重置
      </Button>
      <Button
        size="small"
        @click="handleConfirm">
        确定
      </Button>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { Button } from 'tdesign-vue-next';
  import { computed, shallowRef, watch } from 'vue';

  import { comType } from '@components/db-quick-serach/bk-quick-search/constants';
  import type { IValue, Props as ContextProps } from '@components/db-quick-serach/bk-quick-search/Index.vue';

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
    keyword?: string;
  }

  type Emits = (e: 'change', value: IValue['values']) => void;

  const props = withDefaults(defineProps<Props>(), {
    config: undefined,
    keyword: '',
  });
  const emits = defineEmits<Emits>();

  // modelValue 类型支持所有值，由各个组件自行处理
  const modelValue = defineModel<any[]>();

  const isRemoteListLoading = ref(true);
  const remoteList = shallowRef<any[]>([]);

  const isRemoteList = computed(() => _.isFunction(props.config?.remoteMethod));

  const renderCom = computed(() => {
    if (!props.config || !props.config.type) {
      return null;
    }
    // remoteList 加载中不渲染任何组件，避免组件对 remoteList 数据类型处理错误
    if (isRemoteList.value && isRemoteListLoading.value) {
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
      list: isRemoteList.value ? remoteList.value : props.config.list || [],
      ...Object.assign({}, props.config.props || {}),
    };
  });

  const isNeedComfirmAndReset = computed(() => {
    if (!props.config) {
      return false;
    }
    return props.config.type
      ? [comType.MULTIPLE, comType.MULTIPLE_CASCADER].includes(props.config.type as comType)
      : Boolean(props.config.showConfirmAndReset);
  });

  const fetchRemoteList = () => {
    if (props.config && isRemoteList.value) {
      isRemoteListLoading.value = true;
      Promise.resolve()
        .then(() =>
          props.config!.remoteMethod!({
            keyword: props.keyword,
          }),
        )
        .then((data) => {
          remoteList.value = data;
        })
        .finally(() => {
          isRemoteListLoading.value = false;
        });
    }
  };

  watch(
    () => props.config,
    () => {
      if (props.config && props.config.remoteMethod) {
        fetchRemoteList();
      }
    },
    {
      immediate: true,
    },
  );

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
    emits('change', modelValue.value!);
  };
</script>
<style lang="less">
  .bk-quick-search-type-menu {
    --td-brand-color: #3f87ff;
    --td-brand-color-hover: #5594fa;

    padding: 0;
    margin: -5px -9px;
    font-size: 12px;

    & > * {
      max-height: 550px;
      min-width: 230px;
      min-height: 32px;
      overflow: hidden auto;
      font-size: 12px;
      pointer-events: all;
    }

    .value-item {
      display: flex;
      height: 32px;
      padding: 0 10px 0 16px;
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

  .bk-quick-search-type-menu-filter-empty {
    padding: 8px 16px;
    color: #63656e;
    text-align: center;
    flex: 1;
  }

  .bk-quick-search-type-menu-footer {
    display: flex;
    justify-content: flex-end;
    padding: 8px 12px;
    border-top: 1px solid #dcdee5;
  }
</style>
