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
                :model-value="displayColumns"
                @change="handleCheckChange">
                <Checkbox
                  v-if="hasCheckAll"
                  v-show="!keyword?.length"
                  check-all
                  class="content-check-all"
                  :label="t('全选')"
                  value="all" />
                <Checkbox
                  v-for="column in columns"
                  v-show="
                    column.field?.toLocaleLowerCase().includes(keyword.toLocaleLowerCase()) ||
                    column.label?.toString().toLocaleLowerCase().includes(keyword.toLocaleLowerCase())
                  "
                  :key="column.field"
                  class="content-check-item"
                  :disabled="!!column.disabled"
                  :label="typeof column.label === 'string' ? column.label : column.field"
                  :value="column.field" />
              </CheckboxGroup>
              <div
                v-else
                class="appearance-settings">
                <div class="appearance-settings-title">
                  {{ t('字体大小') }}
                </div>
                <div class="appearance-settings-content">
                  <RadioGroup v-model:value="fontSize">
                    <RadioButton value="medium">{{ t('标准') }}</RadioButton>
                    <RadioButton value="large">{{ t('偏大') }}</RadioButton>
                  </RadioGroup>
                </div>
                <div class="appearance-settings-title">
                  {{ t('表格行高') }}
                </div>
                <div class="appearance-settings-content">
                  <RadioGroup v-model:value="rowSize">
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
  import { shallowRef } from 'vue';

  import { t } from '../lang/lang';
  import type { BkUiSettings, FontSizeEnum, RowSizeEnum } from '../types/table';

  defineOptions({
    name: 'ColumnSettings',
    inheritAttrs: true,
  });

  const props = defineProps<
    Pick<TableProps, 'displayColumns' | 'onDisplayColumnsChange'> & {
      columns?: BkUiSettings['fields'];
      hasCheckAll?: boolean;
      onChange?: () => void;
    }
  >();
  const fontSize = defineModel<FontSizeEnum>('fontSize', {
    default: 'medium',
    type: String as () => FontSizeEnum,
  });
  const rowSize = defineModel<RowSizeEnum>('rowSize', {
    default: 'medium',
    type: String as () => RowSizeEnum,
  });
  const keyword = shallowRef('');
  const activeTab = shallowRef(0);
  const visible = shallowRef(false);

  const handleCheckChange = (value: CheckboxGroupValue) => {
    props.onDisplayColumnsChange?.(
      props.columns?.filter((item) => value?.includes(item.field) || item.disabled).map((item) => item.field) || [],
    );
  };

  const handleVisibleChange = (visible: boolean) => {
    // 如果隐藏了设置面板，触发 onChange 事件
    if (!visible) {
      props.onChange?.();
    }
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
