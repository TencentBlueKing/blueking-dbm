<template>
  <Popup
    v-model:visible="visible"
    :overlay-inner-style="{ padding: 0, borderRadius: '2px' }"
    :popper-options="{
      placement: 'bottom-end',
      modifiers: [
        {
          name: 'offset',
          options: {
            offset: [-8, -6],
          },
        },
      ],
    }"
    :show-arrow="false"
    trigger="click"
    @visible-change="handleVisibleChange">
    <template #content>
      <div class="bkui-col-settings">
        <slot name="content">
          <div class="settings-header">
            <div
              v-for="(title, index) in [t('字段设置'), t('外观设置')]"
              :key="title"
              class="settings-header-title"
              :class="{ 'is-active': index === activeTab }"
              @click="activeTab = index">
              {{ title }}
            </div>
          </div>
          <div class="settings-wrapper">
            <div
              v-show="activeTab === 0"
              class="settings-wrapper-search">
              <Input
                v-model="keyword"
                clearable
                :placeholder="t('输入关键词')">
                <template #prefix-icon> <SearchIcon /></template>
              </Input>
            </div>
            <div class="settings-wrapper-content">
              <CheckboxGroup
                v-if="activeTab === 0"
                class="content-check-list"
                :model-value="draftChecked"
                @change="handleCheckChange">
                <div
                  v-if="hasCheckAll"
                  v-show="!keyword?.length"
                  class="content-check-all">
                  <Checkbox
                    check-all
                    value="all" />
                  <span>{{ t('全选') }}</span>
                </div>
                <Vuedraggable
                  v-model="draftColumns"
                  :disabled="Boolean(keyword)"
                  handle=".column-drag-handle"
                  item-key="field"
                  :move="handleMove">
                  <template #item="{ element: column }">
                    <div
                      v-show="isColumnMatched(column)"
                      class="content-check-item"
                      :class="{ 'is-disabled': column.disabled }">
                      <Checkbox
                        :disabled="!!column.disabled"
                        :value="column.field" />
                      <span
                        class="column-drag-handle"
                        :class="{ 'is-disabled': column.disabled || keyword }">
                        <DbIcon type="drag" />
                      </span>
                      <span>{{ typeof column.label === 'string' ? column.label : column.field }}</span>
                    </div>
                  </template>
                </Vuedraggable>
              </CheckboxGroup>
              <div
                v-else
                class="appearance-settings">
                <div class="appearance-settings-title">
                  {{ t('字体大小') }}
                </div>
                <div class="appearance-settings-content">
                  <RadioGroup v-model:value="draftFontSize">
                    <RadioButton value="medium">{{ t('标准') }}</RadioButton>
                    <RadioButton value="large">{{ t('偏大') }}</RadioButton>
                  </RadioGroup>
                </div>
                <div class="appearance-settings-title">
                  {{ t('表格行高') }}
                </div>
                <div class="appearance-settings-content">
                  <RadioGroup v-model:value="draftRowSize">
                    <RadioButton value="mini">{{ t('迷你') }}</RadioButton>
                    <RadioButton value="small">{{ t('小') }}</RadioButton>
                    <RadioButton value="medium">{{ t('标准') }}</RadioButton>
                    <RadioButton value="large">{{ t('大') }}</RadioButton>
                  </RadioGroup>
                </div>
                <slot name="appearanceSettings" />
              </div>
            </div>
          </div>
        </slot>
      </div>
    </template>
    <slot name="default">
      <div class="column-settings-icon">
        <SettingIcon />
      </div>
    </slot>
  </Popup>
</template>
<script lang="ts" setup>
  import { SearchIcon, SettingIcon } from 'tdesign-icons-vue-next';
  import type { CheckboxGroupValue, TableProps } from 'tdesign-vue-next';
  import { Checkbox, CheckboxGroup, Input, Popup, RadioButton, RadioGroup } from 'tdesign-vue-next';
  import { ref, shallowRef } from 'vue';
  import Vuedraggable from 'vuedraggable';

  import { t } from '../lang/lang';
  import type { BkUiSettingsField, FontSizeEnum, RowSizeEnum } from '../types/table';

  interface Props {
    columns?: BkUiSettingsField[];
    displayColumns?: TableProps['displayColumns'];
    fontSize?: FontSizeEnum;
    hasCheckAll?: boolean;
    onColumnControllerVisibleChange?: (visible: boolean, trigger: 'cancel' | 'confirm' | 'open') => void;
    onConfirm?: (settings: {
      columns: string[];
      fontSize: FontSizeEnum;
      order: string[];
      rowSize: RowSizeEnum;
    }) => void;
    order?: string[];
    rowSize?: RowSizeEnum;
  }

  interface DragMoveEvent {
    draggedContext: {
      element: BkUiSettingsField;
    };
    relatedContext: {
      element?: BkUiSettingsField;
    };
  }

  defineOptions({
    name: 'ColumnSettings',
    inheritAttrs: true,
  });

  const props = withDefaults(defineProps<Props>(), {
    columns: () => [],
    displayColumns: () => [],
    fontSize: 'medium',
    hasCheckAll: false,
    onColumnControllerVisibleChange: undefined,
    onConfirm: undefined,
    order: () => [],
    rowSize: 'medium',
  });

  const keyword = shallowRef('');
  const activeTab = shallowRef(0);
  const visible = shallowRef(false);
  const draftColumns = ref<BkUiSettingsField[]>([]);
  const draftChecked = ref<string[]>([]);
  const draftFontSize = shallowRef<FontSizeEnum>('medium');
  const draftRowSize = shallowRef<RowSizeEnum>('medium');

  const handleCheckChange = (value: CheckboxGroupValue) => {
    draftChecked.value = draftColumns.value
      .filter((item) => value?.includes(item.field) || item.disabled)
      .map((item) => item.field);
  };

  const initDraft = () => {
    const columnMap = new Map(props.columns.map((column) => [column.field, column]));
    const orderedColumns = props.order.map((field) => columnMap.get(field)).filter((column) => column !== undefined);
    const orderedSet = new Set(orderedColumns);
    draftColumns.value = orderedColumns.concat(props.columns.filter((column) => !orderedSet.has(column)));
    const displayColumns = (props.displayColumns ?? []).filter((field): field is string => typeof field === 'string');
    draftChecked.value = Array.from(
      new Set(displayColumns.concat(props.columns.filter((column) => column.disabled).map((column) => column.field))),
    );
    draftFontSize.value = props.fontSize;
    draftRowSize.value = props.rowSize;
    keyword.value = '';
    activeTab.value = 0;
  };

  const handleVisibleChange = (nextVisible: boolean) => {
    if (nextVisible) {
      initDraft();
      props.onColumnControllerVisibleChange?.(true, 'open');
      return;
    }
    props.onConfirm?.({
      columns: draftColumns.value
        .filter((column) => draftChecked.value.includes(column.field) || column.disabled)
        .map((column) => column.field),
      fontSize: draftFontSize.value,
      order: draftColumns.value.map((column) => column.field),
      rowSize: draftRowSize.value,
    });
    props.onColumnControllerVisibleChange?.(false, 'confirm');
  };

  const isColumnMatched = (column: BkUiSettingsField) => {
    const normalizedKeyword = keyword.value.toLocaleLowerCase();
    return (
      column.field.toLocaleLowerCase().includes(normalizedKeyword) ||
      column.label.toString().toLocaleLowerCase().includes(normalizedKeyword)
    );
  };

  const handleMove = (event: DragMoveEvent) => {
    return !event.draggedContext.element.disabled && !event.relatedContext.element?.disabled;
  };
</script>
<style lang="less">
  /* stylelint-disable declaration-no-important */
  .bkui-col-settings {
    display: flex;
    height: fit-content;
    max-height: 500px;
    min-width: 285px;
    min-height: 220px;
    overflow: hidden;
    font-size: 14px;
    color: #4d4f56;
    border-radius: 2px;
    flex-direction: column;

    .settings-header {
      position: relative;
      z-index: 0;
      display: flex;
      flex: 0 0 42px;
      height: 42px;
      margin: 0.5px 0.5px 0;

      &-title {
        display: flex;
        flex: 1;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        background-color: #f0f1f5;

        &.is-active {
          color: #3a84ff;
          background-color: #fff;
        }
      }
    }

    .settings-wrapper {
      flex: 1;
      max-height: 100%;
      padding: 12px 16px;
      overflow: auto;

      &-search {
        .t-input {
          border: none;
          border-bottom: 1px solid #e1e3e6;
          border-radius: 0;
          box-shadow: none !important;
        }
      }

      &-content {
        display: flex;
        flex: 1;
        flex-direction: column;
        padding-top: 8px;

        .content-check-list {
          display: flex;
          flex-direction: column;
          gap: 0;

          .content-check-item,
          .content-check-all {
            display: flex;
            flex: 0 0 32px;
            align-items: center;
            height: 32px;
          }

          .content-check-item {
            width: 100%;

            .t-checkbox__label {
              margin-left: 0;
            }

            .column-drag-handle {
              display: inline-flex;
              padding: 8px;
              color: #979ba5;
              cursor: move;

              &.is-disabled {
                color: #c4c6cc;
                cursor: not-allowed;
              }
            }
          }
        }

        .appearance-settings {
          display: flex;
          flex-direction: column;

          &-title {
            margin-bottom: 8px;
            color: #63656e;
          }

          &-content {
            display: flex;
            align-items: center;
            margin-bottom: 24px;
          }
        }
      }
    }
  }

  .column-settings-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    margin: auto;
    font-size: 14px;
    cursor: pointer;
  }
</style>
