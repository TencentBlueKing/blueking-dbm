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
  <BkPopover
    v-model:is-show="isShow"
    :arrow="false"
    :boundary="body"
    fix-on-boundary
    placement="top-start"
    theme="light range-input"
    trigger="manual"
    :width="330">
    <div
      ref="rangeInputRef"
      v-clickoutside:[rangeContentRef]="handleClose"
      class="range-input__text"
      :class="[{ 'is-focus': isShow }]"
      @click="handleShow">
      <template v-if="showPlaceholder">
        <span style="color: #c4c6cc">{{ $t('请设置范围值') }}</span>
      </template>
      <template v-else> {{ min }}～{{ max }} </template>
    </div>
    <template #content>
      <div
        ref="rangeContentRef"
        class="range-input__content">
        <div class="range-input__title">
          <strong>{{ $t('范围值') }}</strong>
        </div>
        <div class="range-input__value">
          <BkInput
            v-model="valueState.min"
            :max="valueState.max"
            size="small"
            type="number"
            @change="(value) => handleValueChange('min', value)"
            @enter="handleEnter" />
          <span class="pl-8 pr-8">～</span>
          <BkInput
            v-model="valueState.max"
            :min="valueState.min"
            size="small"
            type="number"
            @change="(value) => handleValueChange('max', value)"
            @enter="handleEnter" />
        </div>
      </div>
    </template>
  </BkPopover>
</template>
<script lang="ts">
  export default {
    name: 'RangeInput',
  };
</script>

<script setup lang="ts">
  interface Emits {
    (e: 'change', value: {
      min: number
      max: number
    }): void
  }

  const emits = defineEmits<Emits>();
  const min = defineModel<number>('min', {
    required: true,
  });
  const max = defineModel<number>('max', {
    required: true,
  });

  const { body } = document;
  const rangeContentRef = ref<HTMLElement>();
  const valueState = reactive({
    max: max.value ?? 0,
    min: min.value ?? 0,
  });
  const showPlaceholder = computed(() => !Number.isFinite(max.value) || !Number.isFinite(min.value));

  /**
   * popover control
   */
  const isShow = ref(false);
  const handleShow = () => {
    isShow.value = true;
  };
  const handleClose = () => {
    isShow.value = false;
  };

  /**
   * emit value
   */
  const handleValueChange = (emitName: 'min' | 'max', value: number | string) => {
    if (value === '') return;
    if (emitName === 'min') {
      min.value = Number(value);
    } else {
      max.value = Number(value);
    }
  };

  watch([() => valueState.max, () => valueState.min], ([max, min]) => {
    if (Number.isFinite(max) && Number.isFinite(min)) {
      emits('change', { max: Number(max), min: Number(min) });
    }
  });

  /**
   * 验证值符合校验则关闭popover
   */
  const handleEnter = () => {
    if (Number.isFinite(max.value) && Number.isFinite(min.value) && valueState.min <= valueState.max) {
      handleClose();
    }
  };

  // 当元素被滚动出可视区域则关闭 popover
  const rangeInputRef = ref<HTMLDivElement>();
  onMounted(() => {
    const targetParant = rangeInputRef.value?.closest?.('.bk-table-body');
    if (targetParant) {
      const intersectionObserver = new IntersectionObserver(() => {
        if (isShow.value) {
          isShow.value = false;
        }
      }, {
        root: targetParant,
        threshold: 0,
      });
      rangeInputRef.value && intersectionObserver.observe(rangeInputRef.value);
    }
  });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .range-input__text {
    width: 100%;
    height: 32px;
    padding: 0 10px;
    line-height: 32px;
    color: @default-color;
    vertical-align: middle;
    cursor: pointer;
    // background-color: @bg-white;
    border: 1px solid transparent;
    border-radius: 2px;

    &.is-focus {
      border-color: @primary-color;
    }
  }

  .range-input__content {
    position: relative;
    padding: 9px 2px;
  }

  .range-input__title {
    margin-bottom: 8px;
    color: @title-color;
  }

  .range-input__value {
    .flex-center();

    .bk-slider {
      width: 190px;
      margin: 0 14px;
    }

    .bk-input {
      flex: 1;

      &:not(.is-focused) {
        border-color: transparent;
      }

      :deep(.bk-input--text) {
        background-color: #f5f7fa;
      }

      :deep(.bk-input--number-control) {
        display: none;
      }
    }
  }
</style>
