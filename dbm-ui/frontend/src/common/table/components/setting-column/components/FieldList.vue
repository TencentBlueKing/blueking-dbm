<template>
  <div class="field-list-wrapper">
    <span @click.stop="handleChangeAll">
      <BkCheckbox
        v-model="isCheckedAll"
        :indeterminate="isIndeterminate"
        style="pointer-events: none">
        全选
      </BkCheckbox>
    </span>
    <BkCheckboxGroup v-model="modelValue">
      <div
        v-for="item in list"
        :key="item.field"
        class="field-list-item">
        <BkCheckbox
          :disabled="Boolean(item.disabled)"
          :label="item.field">
          {{ item.title || item.label }}
        </BkCheckbox>
      </div>
    </BkCheckboxGroup>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';

  import { makeMap } from '../../../utils';

  interface Props {
    list: {
      title: string;
      field: string;
      label: string;
      disabled: boolean;
    }[];
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const isCheckedAll = ref(false);
  const isIndeterminate = ref(false);

  const calcCheck = () => {
    isCheckedAll.value = modelValue.value.length > 0;
    isIndeterminate.value = modelValue.value.length > 0;

    const checkedMap = makeMap(modelValue.value);
    props.list.forEach((item) => {
      if (!checkedMap[item.field]) {
        isCheckedAll.value = false;
      }
    });

    if (isCheckedAll.value) {
      isIndeterminate.value = false;
    }
  };

  watch(
    modelValue,
    () => {
      calcCheck();
    },
    {
      immediate: true,
    },
  );

  const handleChangeAll = () => {
    const lastCheckMap = makeMap(modelValue.value);
    if (isCheckedAll.value) {
      modelValue.value = props.list.reduce<string[]>((result, item) => {
        if (item.disabled && lastCheckMap[item.field]) {
          result.push(item.field);
        }
        return result;
      }, []);
    } else {
      modelValue.value = props.list.reduce<string[]>((result, item) => {
        if (!item.disabled) {
          result.push(item.field);
        }
        if (item.disabled && lastCheckMap[item.field]) {
          result.push(item.field);
        }
        return result;
      }, []);
    }
  };
</script>
<style lang="less">
  .tippy-box[data-theme~='bk-vxe-table-setting-column-theme'] {
    .action-tab-wrapper {
      display: flex;
      height: 42px;
      max-height: 500px;
      overflow-y: scroll;
      font-size: 14px;
      color: #63656e;
      background: #f0f1f5;

      .tab-item {
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        transition: all 0.1s;

        &.active {
          color: #3a84ff;
          background: #fff;
        }
      }
    }

    .field-list-wrapper {
      max-height: 300px;
      padding: 0 16px;
      margin: 8px 0;
      overflow-y: auto;

      .bk-checkbox-group {
        display: block;
      }

      .field-list-item {
        display: flex;
        height: 32px;
        align-items: center;
      }
    }
  }
</style>
