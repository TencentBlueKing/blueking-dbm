<template>
  <div class="dimension-select">
    <div style="font-weight: bold">{{ t('聚合维度') }} :</div>
    <div class="select-main">
      <div
        ref="selectTriggerRef"
        class="select-trigger"
        @click="() => (showSelectWrapper = !showSelectWrapper)">
        {{ renderLabel }}
        <DbIcon type="bk-dbm-icon db-icon-down-big" />
      </div>
      <BkRadioGroup
        v-if="showSelectWrapper"
        ref="selectWrapperRef"
        v-model="modelValue"
        class="select-wrapper"
        @change="changeDimension">
        <BkRadio
          v-for="item in dimensions"
          :key="item.value"
          class="select-item"
          :label="item.value">
          {{ item.label }}
        </BkRadio>
      </BkRadioGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Emits {
    (e: 'change', value: string): void;
  }

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: 'spec',
  });

  const { t } = useI18n();

  const dimensions = [
    {
      label: t('地域 + 规格'),
      value: 'spec',
    },
    {
      label: t('地域 + 机型（硬盘）'),
      value: 'device_class',
    },
  ];

  const selectTriggerRef = ref();
  const selectWrapperRef = ref();
  const showSelectWrapper = ref(false);

  const renderLabel = computed(() => dimensions.find((item) => item.value === modelValue.value)?.label as string);

  const changeDimension = (value: string) => {
    showSelectWrapper.value = false;
    emits('change', value);
  };
</script>

<style lang="less" scoped>
  .dimension-select {
    display: flex;
    margin: 16px 0;
    align-items: center;

    .select-main {
      padding: 0 6px;

      .select-trigger {
        font-size: 12px;
        color: #313238;
        cursor: pointer;
      }

      .select-wrapper {
        position: fixed;
        z-index: 9999;
        display: flex;
        width: 219px;
        height: 73px;
        background: #fff;
        border: 1px solid #dcdee5;
        border-radius: 2px;
        transform: translateY(6px);
        box-shadow: 0 2px 6px 0 #0000001a;
        flex-direction: column;
        justify-content: center;
        align-items: center;

        :deep(.bk-radio) {
          & ~ .bk-radio {
            margin-left: 0;
          }

          .bk-radio-label {
            font-size: 12px;
          }
        }

        .select-item {
          width: 217px;
          height: 32px;
          padding-left: 12px;

          &:hover {
            background: #f5f7fa;
          }
        }
      }
    }
  }
</style>
