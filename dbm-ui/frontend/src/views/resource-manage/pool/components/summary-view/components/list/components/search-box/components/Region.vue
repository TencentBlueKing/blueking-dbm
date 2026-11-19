<template>
  <BkComposeFormItem class="search-box-select-region">
    <DbSelect
      v-model="region"
      clearable
      style="width: 100px"
      @change="handleChangeRegion">
      <DbOption
        v-for="item in regionList"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </DbSelect>
    <DbSelect
      v-model="subzoneIds"
      collapse-tags
      :disabled="!region"
      filterable
      multiple
      multiple-mode="tag"
      show-select-all
      @change="handleChangeSubzone">
      <DbOption
        v-for="item in renderSubzoneList"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </DbSelect>
  </BkComposeFormItem>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getInfrasCloudRegions, getInfrasSubzonesByCity } from '@services/source/infras';

  import { specialOptionLabelMap, SpecialOptions } from '@common/const';

  interface Props {
    model: Record<string, string>;
  }

  type Emits = (
    e: 'change',
    value: {
      city: string;
      subzone_ids: string;
    },
  ) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const region = ref('');
  const subzoneIds = ref<string[]>([]);

  const renderSubzoneList = computed(() => {
    const emptyItem = {
      label: specialOptionLabelMap[SpecialOptions.EMPTY],
      value: SpecialOptions.EMPTY,
    };

    if (region.value === SpecialOptions.EMPTY) {
      return [emptyItem];
    }

    return (subzoneList.value || [])
      .filter((item) => item.bk_cloud_region === region.value)
      .map((item) => ({
        label: item.bk_sub_zone,
        value: `${item.bk_sub_zone_id}`,
      }))
      .concat(emptyItem);
  });

  const regionList = ref<{ label: string; value: string }[]>([]);

  // 地域候选：全量地域 + 筛空值项
  useRequest(getInfrasCloudRegions, {
    onSuccess(data) {
      regionList.value = data
        .map((item) => ({
          label: item.display_name,
          value: item.bk_cloud_region,
        }))
        .concat({
          label: specialOptionLabelMap[SpecialOptions.EMPTY],
          value: SpecialOptions.EMPTY,
        });
    },
  });
  const { data: subzoneList } = useRequest(getInfrasSubzonesByCity);

  watch(
    () => props.model,
    () => {
      if (props.model.city) {
        region.value = props.model.city;
      }
      if (props.model.subzone_ids) {
        subzoneIds.value = props.model.subzone_ids.split(',');
      }
    },
    {
      immediate: true,
    },
  );

  const getLocalValue = () => ({
    city: region.value,
    subzone_ids: subzoneIds.value.join(','),
  });

  const handleChangeRegion = () => {
    subzoneIds.value = [];
    emits('change', getLocalValue());
  };

  const handleChangeSubzone = () => {
    emits('change', getLocalValue());
  };
</script>

<style lang="less" scoped>
  .search-box-select-region {
    display: flex;
    width: 100%;

    :deep(.bk-compose-form-item-tail) {
      flex: 1;
    }
  }
</style>
