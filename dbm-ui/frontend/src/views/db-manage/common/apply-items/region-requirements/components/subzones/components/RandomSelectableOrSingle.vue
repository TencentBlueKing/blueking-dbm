<template>
  <BkCheckbox
    v-model="isRandom"
    :disabled="isAdjustApply"
    @change="handleCheckAllChange">
    {{ t('随机') }}
  </BkCheckbox>
  <div
    v-if="subzoneList?.length"
    class="subzone-bar" />
  <BkRadioGroup
    v-model="subzoneLocalValue"
    :disabled="isAdjustApply"
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

  import { useTicketModifyState } from '@hooks';

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

  // 调整申请只能改规格与资源标签，容灾级别、地域、园区只读
  const isAdjustApply = Boolean(useTicketModifyState()?.isAdjustApply);

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
    // 空数组即随机园区，界面同步回随机，否则重置后仍显示之前选中的园区
    setInitSubzone(subzoneIds: number[]) {
      isRandom.value = subzoneIds.length < 1;
      subzoneLocalValue.value = subzoneIds[0] ?? 0;
    },
  });
</script>
