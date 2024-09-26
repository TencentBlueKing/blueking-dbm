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
        :key="item.bk_sub_zone_id"
        :label="item.bk_sub_zone"
        :value="`${item.bk_sub_zone_id}`" />
    </BkSelect>
  </BkComposeFormItem>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getInfrasCities, getInfrasSubzonesByCity } from '@services/source/infras';

  type CityItem = ServiceReturnType<typeof getInfrasCities>[number];

  interface Props {
    model: Record<string, string>;
  }

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      city: string;
      subzone_ids: string;
    };
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const citiyList = ref<CityItem[]>([]);
  const cityCode = ref('');
  const subzoneIds = ref<string[]>([]);

  const renderSubzoneList = computed(() =>
    (subzoneList.value || []).filter((item) => item.bk_city_code === cityCode.value),
  );

  useRequest(getInfrasCities, {
    onSuccess(data) {
      citiyList.value = data.filter((item) => item.city_code !== 'default');
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

  const handleChangeCity = () => {
    subzoneIds.value = [];
    emits('change');
  };

  const handleChangeSubzone = () => {
    emits('change');
  };

  defineExpose<Exposes>({
    getValue: () => ({
      city: cityCode.value,
      subzone_ids: subzoneIds.value.join(','),
    }),
  });
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
