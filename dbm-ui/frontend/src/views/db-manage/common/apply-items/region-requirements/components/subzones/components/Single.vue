<template>
  <BkRadioGroup
    v-model="localValue"
    @change="handleChange">
    <BkRadio
      v-for="item in subzoneList"
      :key="item.bk_sub_zone_id"
      :label="item.bk_sub_zone_id">
      {{ item.bk_sub_zone }}
    </BkRadio>
  </BkRadioGroup>
</template>

<script setup lang="ts">
  import { getInfrasSubzonesByCity } from '@services/source/infras';

  interface Props {
    subzoneList?: ServiceReturnType<typeof getInfrasSubzonesByCity>;
  }

  interface Expose {
    setInitSubzone(subzoneIds: number[]): void;
  }

  defineProps<Props>();

  const modelValue = defineModel<number[]>({
    required: true,
  });

  const localValue = ref<number>();

  const handleChange = (value: number) => {
    modelValue.value = [value];
  };

  defineExpose<Expose>({
    // 空数组时同步清空界面，否则重置后仍显示之前选中的园区
    setInitSubzone(subzoneIds: number[]) {
      localValue.value = subzoneIds[0];
    },
  });
</script>
