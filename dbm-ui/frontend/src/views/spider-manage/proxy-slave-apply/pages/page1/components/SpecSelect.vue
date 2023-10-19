<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div
    ref="rootRef"
    class="table-edit-select"
    :class="{
      'is-focused': isShowPop,
      'is-error': Boolean(errorMessage),
      'is-disabled': disabled,
      'is-seleced': !!localValue
    }">
    <!-- <div class="select-result-text">
      <span>{{ renderText }}</span>
    </div>
    <DbIcon
      v-if="localValue"
      class="remove-btn"
      type="delete-fill"
      @click.self="handleRemove" />
    <DbIcon
      class="focused-flag"
      type="down-big" /> -->
    <div
      v-if="errorMessage"
      class="select-error">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <BkSelect
      v-model="localValue"
      auto-focus
      class="select-box"
      :clearable="false"
      :disabled="disabled"
      filterable
      :input-search="false"
      :placeholder="placeholder"
      show-select-all
      @change="handleSelect"
      @clear="handleRemove">
      <SpecPanel
        v-for="item in renderList"
        :key="item.id"
        :data="item.specData">
        <template #hover>
          <BkOption
            :label="item.name"
            :value="item.id">
            <div
              class="tendb-slave-apply-option-item"
              :class="{
                active: item.id === localValue
              }"
              @click="handleSelect(item)">
              <span>{{ item.name }}</span>
              <span
                class="spec-display-count"
                :class="{'count-active': item.id === localValue}">{{ item.specData.count }}</span>
            </div>
          </BkOption>
        </template>
      </SpecPanel>
    </BkSelect>
  </div>
</template>
<script setup lang="ts">

  import { useDebouncedRef } from '@hooks';

  import useValidtor, {
    type Rules,
  } from '@views/redis/common/edit/hooks/useValidtor';

  import { encodeRegexp } from '@utils';

  import type { SpecInfo } from './SpecPanel.vue';
  import SpecPanel from './SpecPanel.vue';

  type IKey = string | number

  export interface IListItem {
    id: number,
    name: string,
    specData: SpecInfo
  }

  interface Props {
    list: Array<IListItem>,
    placeholder?: string,
    rules?: Rules,
    disabled?: boolean
  }
  interface Emits {
    (e: 'change', value: IKey): void
  }

  interface Exposes {
    getValue: () => Promise<IKey>;
  }

  const props = withDefaults(defineProps<Props>(), {
    placeholder: '请输入',
    textarea: false,
    rules: () => [],
    disabled: false,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IKey>({
    default: '',
  });

  const localValue = ref<IKey>('');
  const isShowPop = ref(false);
  const timer = ref();
  const selectList = ref<Array<IListItem>>([]);

  const renderList = computed({
    get() {
      return selectList.value.reduce((result, item) => {
        const reg = new RegExp(encodeRegexp(searchKey.value), 'i');
        if (reg.test(item.name)) {
          result.push(item);
        }
        return result;
      }, [] as Array<IListItem>);
    },
    set(value) {
      selectList.value = value;
    },
  });
  const searchKey = useDebouncedRef('');

  const {
    message: errorMessage,
    validator,
  } = useValidtor(props.rules);


  watch(() => props.list, (list) => {
    if (list.length > 0) {
      selectList.value = list;
    }
  }, {
    immediate: true,
  });

  watch(modelValue, (value) => {
    localValue.value = value;
  }, {
    immediate: true,
  });

  // 选择
  const handleSelect = (item: IListItem) => {
    clearTimeout(timer.value);
    localValue.value = item.id;

    validator(localValue.value)
      .then(() => {
        window.changeConfirm = true;
        modelValue.value = localValue.value;
        emits('change', localValue.value);
      });
  };
  // 删除值
  const handleRemove = () => {
    localValue.value = '';
    validator(localValue.value)
      .then(() => {
        window.changeConfirm = true;
        modelValue.value = '';
        emits('change', localValue.value);
      });
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localValue.value)
        .then(() => localValue.value);
    },
  });

</script>
<style lang="less" scoped>
.table-edit-select {
  position: relative;
  height: 42px;
  overflow: hidden;
  color: #63656e;
  cursor: pointer;
  border: 1px solid transparent;
  transition: all 0.15s;

  &:hover {
    background-color: #fafbfd;
    border-color: #a3c5fd;
  }

  :deep(.select-box) {
    width: 100%;
    height: 100%;
    padding: 0;
    background: transparent;
    border: none;
    outline: none;

    .bk-select-trigger {
      height: 100%;
      background: inherit;

      .bk-input {
        height: 100%;
        border: none;
        outline: none;

        input {
          background: transparent;
        }
      }
    }
  }

  &.is-error {
    background: rgb(255 221 221 / 20%);

    .focused-flag {
      display: none;
    }
  }

  &.is-disabled {
    cursor: not-allowed;
    background-color: #fafbfd;
  }


  .select-error {
    position: absolute;
    top: 0;
    right: 0;
    bottom: 0;
    z-index: 99;
    display: flex;
    padding-right: 6px;
    font-size: 14px;
    color: #ea3636;
    align-items: center;
  }
}

</style>

<style lang="less">
.bk-select-popover {
  .bk-select-content-wrapper {
    .bk-select-content {
      .bk-select-dropdown {
        .bk-select-option {
          .tendb-slave-apply-option-item {
            display: flex;
            width: 100%;
            justify-content: space-between;
            align-items: center;

            .spec-display-count {
              height: 16px;
              min-width: 20px;
              font-size: 12px;
              line-height: 16px;
              color: @gray-color;
              text-align:center;
              background-color: #F0F1F5;
              border-radius: 2px;
            }

            .count-active {
              color: white;
              background-color: #A3C5FD;
            }
          }
        }
      }
    }
  }

}
</style>
