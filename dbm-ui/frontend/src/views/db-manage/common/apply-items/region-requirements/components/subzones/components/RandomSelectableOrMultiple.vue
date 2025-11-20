<template>
  <BkCheckbox
    v-model="isRandom"
    @change="handleRandomChange">
    {{ t('随机') }}
  </BkCheckbox>
  <div
    v-if="subzoneList?.length"
    class="subzone-bar" />
  <BkCheckboxGroup
    :key="subzoneList?.join(',')"
    v-model="subzoneLocalValue"
    v-bk-tooltips="t('至少选择n个区', { n: 2 })"
    @change="handleMutipleChange">
    <BkCheckbox
      v-for="item in subzoneList"
      :key="item.bk_sub_zone_id"
      :label="item.bk_sub_zone_id">
      {{ item.bk_sub_zone }}
    </BkCheckbox>
  </BkCheckboxGroup>
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
  const subzoneLocalValue = ref<number[]>([]);

  watch(
    () => props.cityCode,
    () => {
      isRandom.value = true;
      subzoneLocalValue.value = [];
    },
  );

  const handleRandomChange = (value: boolean) => {
    if (value) {
      subzoneLocalValue.value = [];
    }
    modelValue.value = [];
  };

  const handleMutipleChange = (value: number[]) => {
    modelValue.value = value;
    isRandom.value = value.length ? false : true;
  };

  defineExpose<Expose>({
    setInitSubzone(subzoneIds: number[]) {
      if (subzoneIds.length > 0) {
        isRandom.value = false;
        subzoneLocalValue.value = subzoneIds;
      }
    },
  });
</script>
