<template>
  <div
    ref="root"
    class="bk-quick-search-suggest-menu">
    <div
      v-for="(item, index) in renderList"
      :key="index"
      class="suggest-item"
      :class="{ active: activeIndex === index }"
      @click="handleChange(item)">
      <div class="suggest-item-label">{{ item.name }}:</div>
      <div class="suggest-item-value">
        {{ getValuesText(item.values) }}
      </div>
    </div>
    <div
      v-if="renderList.length < 1"
      class="bk-quick-search-suggest-menu-empty">
      不支持搜索 "
      <span>
        {{ keyword }}
      </span>
      " 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, useTemplateRef, watch } from 'vue';

  import { comType } from '@components/db-quick-search/bk-quick-search/constants';
  import useMenuKeyboard from '@components/db-quick-search/bk-quick-search/hooks/useMenuKeyboard';
  import type { IValue, Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { BK_QUICK_SEARCH } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { calcNeedShowValueMenu, getValuesText } from '@components/db-quick-search/bk-quick-search/utils';

  interface Props {
    data: ContextProps['data'];
    keyword: string;
  }

  type Emits = (e: 'change', value: IValue) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const context = inject(BK_QUICK_SEARCH);

  const rootRef = useTemplateRef('root');

  const renderList = computed(() => {
    const valueList = context!.pasteParseMethod(props.keyword);
    const result: IValue[] = [];

    if (valueList.length === 1) {
      const valueWord = valueList[0]!;
      props.data.forEach((dataItem) => {
        // 数据来自服务端，不支持自动匹配
        if (dataItem.remoteSearch || _.isFunction(dataItem.remoteMethod)) {
          return;
        }
        // 从备选列表匹配
        if (_.isArray(dataItem.list)) {
          dataItem.list.forEach((childItem) => {
            if (dataItem.type && [comType.MULTIPLE, comType.SINGLE].includes(dataItem.type as comType)) {
              if (childItem.label.indexOf(valueWord) > -1) {
                result.push({
                  id: dataItem.id,
                  name: dataItem.name,
                  values: [
                    {
                      label: childItem.label,
                      value: childItem.value,
                    },
                  ],
                });
              }
            }
            if (dataItem.type && [comType.CASCADER, comType.MULTIPLE_CASCADER].includes(dataItem.type as comType)) {
              childItem.children?.forEach((grandChildItem) => {
                if (grandChildItem.label.indexOf(valueWord) > -1) {
                  result.push({
                    id: dataItem.id,
                    name: dataItem.name,
                    values: [
                      {
                        label: grandChildItem.label,
                        value: grandChildItem.value,
                      },
                    ],
                  });
                }
              });
            }
          });
          return;
        }

        // 时间不支持直接输入
        let validatorResult = dataItem.type
          ? ![comType.DATE, comType.DATE_RANGE, comType.DATETIME, comType.DATETIME_RANGE].includes(
              dataItem.type as comType,
            )
          : true;

        if (_.isFunction(dataItem.validator) && dataItem.validator(valueWord) !== true) {
          validatorResult = false;
        }
        if (validatorResult) {
          result.push({
            id: dataItem.id,
            name: dataItem.name,
            values: [
              {
                label: valueWord,
                value: valueWord,
              },
            ],
          });
        }
      });
    }

    if (valueList.length > 1) {
      for (const dataItem of props.data) {
        if (calcNeedShowValueMenu(dataItem)) {
          continue;
        }
        let validatorResult = true;
        if (_.isFunction(dataItem.validator)) {
          validatorResult = _.every(valueList, (item) => dataItem.validator!(item) === true);
        }

        // 命中了一个可选项后不在检索后面的
        if (validatorResult) {
          result.push({
            id: dataItem.id,
            name: dataItem.name,
            values: valueList.map((item) => ({
              label: item,
              value: item,
            })),
          });
          break;
        }
      }
    }

    return result;
  });

  const handleChange = (value: IValue) => {
    emits('change', value);
  };

  const { activeIndex } = useMenuKeyboard(renderList, rootRef, (value) => {
    handleChange(value);
  });

  watch(
    renderList,
    () => {
      const defaultData = _.find(props.data, (item) => Boolean(item.default));
      if (!defaultData) {
        return;
      }
      const defaultValueIndex = _.findIndex(renderList.value, (item) => item.id === defaultData.id);
      if (defaultValueIndex > -1) {
        activeIndex.value = defaultValueIndex;
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .bk-quick-search-suggest-menu {
    max-height: 350px;
    min-width: 230px;
    min-height: 32px;
    padding: 8px 0;
    margin: -5px -9px;
    overflow: hidden auto;
    font-size: 12px;
    pointer-events: all;

    .suggest-item {
      display: flex;
      height: 32px;
      max-width: 500px;
      padding: 0 12px;
      overflow: hidden;
      font-size: 12px;
      color: #63656e;
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

      .suggest-item-label {
        padding-right: 4px;
        font-weight: bold;
      }

      .suggest-item-value {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        pointer-events: auto;
      }
    }
  }

  .bk-quick-search-suggest-menu-empty {
    display: flex;
    max-width: 30vw;
    padding: 8px 16px;
    overflow: hidden;
    color: #63656e;
    text-align: center;
    white-space: nowrap;

    span {
      display: inline-flex;
      flex: 0 1 auto;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
