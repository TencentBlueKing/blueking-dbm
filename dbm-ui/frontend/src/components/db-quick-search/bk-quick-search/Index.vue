<template>
  <div
    ref="rootRef"
    class="bk-quick-search"
    :class="{
      'is-focused': isFouced,
      'is-error': Boolean(errorMessage),
    }">
    <div
      class="bk-quick-search-wrapper"
      @click="handleFocus">
      <div class="bk-quick-search-tag-box">
        <CalcRenderNum
          key="calcRenderNum"
          v-model="renderTagCount"
          :data="data"
          :fouced="isFouced"
          :value-list="localSelectValueList" />
        <template
          v-for="(item, index) in renderTagList"
          :key="item.id">
          <RenderValue
            :data="data"
            :value="item"
            @change="(value) => handleValueTagEditChange(value, index)"
            @error="handleError"
            @remove="handleValueTagRemove(item)" />
        </template>
        <TagFlod
          v-if="!isFouced"
          key="tagFlod"
          :data="data"
          :render-tag-count="renderTagCount"
          :value-list="localSelectValueList" />
        <CreateArea
          v-if="(isFouced || isSelectedValueEmpty) && toBeSelectData.length > 0"
          key="createArea"
          :data="toBeSelectData"
          :default-start-select="isFoucedStartSelect"
          :placeholder="placeholder"
          @change="handleChange"
          @error="handleError"
          @remove="handleRemove" />
      </div>
      <div
        v-if="localSelectValueList.length > 0 && clearable"
        class="bk-quick-search-clear-btn"
        @click="handleClear">
        <Icon name="close-circle-filled" />
      </div>
      <div
        v-if="errorMessage"
        class="bk-quick-search-error">
        {{ errorMessage }}
      </div>
    </div>
  </div>
</template>
<script lang="tsx">
  import _ from 'lodash';
  import { Icon } from 'tdesign-vue-next';
  import { computed, type InjectionKey, provide, reactive, ref, shallowRef, watch } from 'vue';

  import { hideAll } from '@components/db-quick-search/bk-quick-search/hooks/useMenuPop';

  import CalcRenderNum from './components/CalcRenderNum.vue';
  import CreateArea from './components/create-area/Index.vue';
  import RenderValue from './components/render-value/Index.vue';
  import TagFlod from './components/TagFlod.vue';
  import { comType } from './constants';
  import { update as updateMenuPop } from './hooks/useMenuPop';
  import useOutSideClick from './hooks/useOutSideClick';

  export interface IValue {
    id: string | number;
    name: string;
    values: {
      label: string;
      value: string | number;
    }[];
  }

  export interface Props {
    changeTrigger?: 'blur' | 'change';
    clearable?: boolean;
    data: {
      component?: any;
      default?: boolean;
      description?: string;
      id: string;
      list?: {
        children?: {
          label: string;
          value: string | number;
        }[];
        label: string;
        value: string | number;
      }[];
      name: string;
      pasteParseMethod?: (value: string) => string[];
      placeholder?: string;
      props?: Record<string, any>;
      remoteMethod?: (params?: any) => Promise<
        {
          children?: {
            label: string;
            value: string | number;
          }[];
          label: string;
          value: string | number;
        }[]
      >;
      remoteSearch?: boolean;
      showConfirmAndReset?: boolean;
      type?: `${comType}`;
      validator?: (value: string) => boolean | string;
    }[];
    pasteParseMethod?: (value: string) => string[];
    placeholder?: string;
  }

  export type Emits = (event: 'change', value: IValue[]) => void;

  export const BK_QUICK_SEARCH: InjectionKey<{
    isFouced: boolean;
    pasteParseMethod: NonNullable<Props['pasteParseMethod']>;
  }> = Symbol.for('bk-quick-search');
</script>
<script setup lang="tsx">
  const props = withDefaults(defineProps<Props>(), {
    changeTrigger: 'change',
    clearable: true,
    pasteParseMethod: (text: string) =>
      _.uniq(_.filter(text.split(/[ \r\n\t,，;；|｜]/g), (item) => Boolean(_.trim(item)))),
    placeholder: '请选择搜索项',
  });

  const emits = defineEmits<Emits>();
  const slots = defineSlots<Slots>();

  const modelValue = defineModel<IValue[]>({
    default: () => [],
  });
  const rootRef = ref<HTMLElement>();
  const isFouced = ref(false);
  // 获得焦点时是否开始选择。如果是点击已选择的 tag 进入编辑状态获得焦点，则不开始选择
  const isFoucedStartSelect = ref(false);
  const errorMessage = ref('');
  const renderTagCount = ref(0);
  const localSelectValueList = shallowRef<IValue[]>([]);

  const isSelectedValueEmpty = computed(() => localSelectValueList.value.length < 1);

  const toBeSelectData = computed(() => {
    const selectedIdMap = localSelectValueList.value.reduce(
      (result, item) =>
        Object.assign(result, {
          [item.id]: true,
        }),
      {} as Record<string, boolean>,
    );

    return _.filter(props.data, (item) => !selectedIdMap[item.id]);
  });

  const renderTagList = computed(() => {
    const wholeList = [...localSelectValueList.value];
    if (renderTagCount.value <= 0 || isFouced.value) {
      return wholeList;
    }
    return wholeList.slice(0, renderTagCount.value);
  });

  let lastSelectValueListMemo: IValue[] = [];
  const triggerChange = () => {
    if (lastSelectValueListMemo.length < 1 && localSelectValueList.value.length < 1) {
      return;
    }
    lastSelectValueListMemo = localSelectValueList.value;
    modelValue.value = [...localSelectValueList.value];
    emits('change', [...localSelectValueList.value]);
  };

  useOutSideClick(() => {
    if (!isFouced.value) {
      return;
    }
    isFouced.value = false;
    isFoucedStartSelect.value = false;
    errorMessage.value = '';
    hideAll();
    if (props.changeTrigger === 'blur') {
      triggerChange();
    }
  });

  provide(
    BK_QUICK_SEARCH,
    reactive({
      emits,
      isFouced,
      pasteParseMethod: props.pasteParseMethod,
      slots,
    }),
  );

  watch(
    modelValue,
    () => {
      localSelectValueList.value = [...modelValue.value];
      lastSelectValueListMemo = localSelectValueList.value;
    },
    {
      immediate: true,
    },
  );

  const changeEventTriggerWithChange = () => {
    if (props.changeTrigger !== 'change') {
      return;
    }
    triggerChange();
  };

  const handleFocus = (event: Event) => {
    // 避免逻辑重复触发
    if (isFouced.value) {
      return;
    }
    isFouced.value = true;
    const eventPath = event.composedPath() as HTMLElement[];
    for (const target of eventPath) {
      // 如果点击的元素是已选择的 tag，则不开始选择
      // 已选择的 tag 的 role 属性为 search-value
      if (target.getAttribute?.('role') === 'search-value') {
        isFoucedStartSelect.value = false;
        return;
      }
    }
    isFoucedStartSelect.value = true;
  };

  const handleValueTagEditChange = (payload: IValue, index: number) => {
    const lastSelectValueList = [...localSelectValueList.value];
    lastSelectValueList[index] = payload;
    localSelectValueList.value = lastSelectValueList;
    changeEventTriggerWithChange();
  };

  const handleValueTagRemove = (payload: IValue) => {
    const lastSelectValueList = [...localSelectValueList.value];
    _.remove(lastSelectValueList, (item) => item === payload);
    localSelectValueList.value = lastSelectValueList;
    changeEventTriggerWithChange();
    updateMenuPop();
  };

  const handleChange = (value: IValue) => {
    const lastSelectValueList = [...localSelectValueList.value];
    _.remove(lastSelectValueList, (item) => item.id === value.id);
    lastSelectValueList.push(value);
    localSelectValueList.value = lastSelectValueList;
    changeEventTriggerWithChange();
  };

  const handleRemove = () => {
    if (localSelectValueList.value.length < 1) {
      return;
    }
    const lastSelectValueList = [...localSelectValueList.value];
    lastSelectValueList.pop();
    localSelectValueList.value = lastSelectValueList;
    changeEventTriggerWithChange();
  };
  const handleClear = () => {
    localSelectValueList.value = [];
    changeEventTriggerWithChange();
    updateMenuPop();
  };

  const handleError = (value: string) => {
    errorMessage.value = value;
  };
</script>
<style lang="less">
  .bk-quick-search {
    position: relative;
    z-index: 9;
    height: 32px;
    font-size: 12px;

    &.is-focused {
      .bk-quick-search-wrapper {
        border-color: #1890ff;
      }

      .bk-quick-search-tag-box {
        height: auto;
        flex-wrap: wrap;
      }
    }
  }

  .bk-quick-search-wrapper {
    position: absolute;
    top: 0;
    right: 0;
    left: 0;
    color: #63656e;
    background: #fff;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
  }

  .bk-quick-search-tag-box {
    display: flex;
    height: 30px;
    max-width: calc(100% - 24px);
    min-height: 30px;
    padding: 0 8px;
    padding-bottom: 4px;
    overflow: hidden;
    box-sizing: border-box;
    transition: border 0.2s linear;
    align-items: flex-start;
  }

  .bk-quick-search-error {
    display: flex;
    padding: 3px 8px;
    font-size: 12px;
    line-height: 16px;
    color: #ea3636;
    align-items: center;
    background: #fff;
  }

  .bk-quick-search-clear-btn {
    position: absolute;
    top: 0;
    right: 0;
    display: flex;
    width: 32px;
    height: 32px;
    font-size: 14px;
    color: #c4c6cc;
    cursor: pointer;
    justify-content: center;
    align-items: center;

    &:hover {
      color: #979ba5;
    }
  }

  [data-tippy-root] .tippy-box[data-theme~='bk-quick-search-panel-theme'] {
    .tippy-content {
      padding: 0;
    }
  }
</style>
