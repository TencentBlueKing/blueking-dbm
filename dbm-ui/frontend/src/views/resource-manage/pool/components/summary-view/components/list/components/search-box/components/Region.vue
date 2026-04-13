<template>
  <BkComposeFormItem class="search-box-select-region">
    <BkSelect
      v-model="cityCode"
      clearable
      style="width: 100px"
      @change="handleChangeCity">
      <BkOption
        v-for="item in citiyList"
        :key="item.city_code"
        :label="item.city_name"
        :value="item.city_code" />
    </BkSelect>
    <BkSelect
      v-model="subzoneIds"
      collapse-tags
      :disabled="!cityCode"
      filterable
      multiple
      multiple-mode="tag"
      show-select-all
      @change="handleChangeSubzone">
      <BkOption
        v-for="item in renderSubzoneList"
        :key="item.value"
        :label="item.label"
        :value="item.value" />
    </BkSelect>
  </BkComposeFormItem>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getCommonCities, getInfrasSubzonesByCity } from '@services/source/infras';

  import { specialOptionLabelMap, SpecialOptions } from '@common/const';

  type CityItem = ServiceReturnType<typeof getCommonCities>['common'][number];

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

  const citiyList = ref<CityItem[]>([]);
  const cityCode = ref('');
  const subzoneIds = ref<string[]>([]);

  const renderSubzoneList = computed(() => {
    const emptyItem = {
      label: specialOptionLabelMap[SpecialOptions.EMPTY],
      value: SpecialOptions.EMPTY,
    };

    if (cityCode.value === SpecialOptions.EMPTY) {
      return [emptyItem];
    }

    return (subzoneList.value || [])
      .filter((item) => item.bk_city_code === cityCode.value)
      .map((item) => ({
        label: item.bk_sub_zone,
        value: `${item.bk_sub_zone_id}`,
      }))
      .concat(emptyItem);
  });

  useRequest(getCommonCities, {
    onSuccess(data) {
      citiyList.value = data.common
        .concat(data.internal)
        .filter((item) => item.city_code !== 'default')
        .concat({
          city_code: SpecialOptions.EMPTY,
          city_name: specialOptionLabelMap[SpecialOptions.EMPTY],
          inventory: 0,
          inventory_tag: '',
        });
    },
  });
  const { data: subzoneList } = useRequest(getInfrasSubzonesByCity);

  watch(
    () => props.model,
    () => {
      if (props.model.city) {
        cityCode.value = props.model.city;
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
    city: cityCode.value,
    subzone_ids: subzoneIds.value.join(','),
  });

  const handleChangeCity = () => {
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
