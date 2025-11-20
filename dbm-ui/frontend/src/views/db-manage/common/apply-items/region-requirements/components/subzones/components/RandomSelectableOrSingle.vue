<template>
  <BkCheckbox
    v-model="isRandom"
    @change="handleCheckAllChange">
    {{ t('随机') }}
  </BkCheckbox>
  <div
    v-if="subzoneList?.length"
    class="subzone-bar" />
  <BkRadioGroup
    v-model="subzoneLocalValue"
    @change="handleSingleChange">
    <BkRadio
      v-for="item in subzoneList"
      :key="item.bk_sub_zone_id"
      :label="item.bk_sub_zone_id">
      {{ item.bk_sub_zone }}
    </BkRadio>
  </BkRadioGroup>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getInfrasSubzonesByCity } from '@services/source/infras';

  interface Props {
    cityCode: string;
    subzoneList?: ServiceReturnType<typeof getInfrasSubzonesByCity>;
  }

  interface Expose {
    setInitSubzone(subzoneIds: number[]): void;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number[]>({
    required: true,
  });

  const { t } = useI18n();

  const isRandom = ref(true);
  const subzoneLocalValue = ref<number>();

  watch(
    () => props.cityCode,
    () => {
      isRandom.value = true;
      subzoneLocalValue.value = 0;
    },
  );

  const handleCheckAllChange = (value: boolean) => {
    if (value) {
      subzoneLocalValue.value = 0;
    }
    modelValue.value = [];
  };

  const handleSingleChange = (value: number) => {
    modelValue.value = [value];
    isRandom.value = false;
  };

  defineExpose<Expose>({
    setInitSubzone(subzoneIds: number[]) {
      if (subzoneIds.length > 0) {
        isRandom.value = false;
        subzoneLocalValue.value = subzoneIds[0];
      }
    },
  });
</script>
