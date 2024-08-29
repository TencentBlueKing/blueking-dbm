<template>
  <BkComposeFormItem class="search-box-select-region">
    <BkSelect
      v-model="cityCode"
      style="width: 100px"
      @change="handleChange">
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
      @change="handleChange">
      <BkOption
        v-for="item in subzoneList"
        :key="item.bk_sub_zone_id"
        :label="item.bk_sub_zone"
        :value="`${item.bk_sub_zone_id}`" />
    </BkSelect>
  </BkComposeFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useRequest } from 'vue-request';

  import { getInfrasCities, getInfrasSubzonesByCity } from '@services/source/infras';

  type CityItem = ServiceReturnType<typeof getInfrasCities>[number];

  interface Emits {
    (e: 'change'): void;
  }

  interface Exposes {
    getValue: () => {
      city: string;
      subzone_ids: string[];
    };
  }

  const emits = defineEmits<Emits>();

  const cityCode = defineModel<string>('cityCode', {
    default: '',
  });

  const subzoneIds = defineModel<string[]>('subzoneIds', {
    default: [],
  });

  const citiyList = ref<CityItem[]>([]);

  useRequest(getInfrasCities, {
    initialData: [],
    onSuccess(data) {
      const cloneData = _.cloneDeep(data);
      cloneData.unshift(cloneData.pop() as CityItem);
      citiyList.value = cloneData;
    },
  });
  const { data: subzoneList, run: fetchData } = useRequest(getInfrasSubzonesByCity, {
    initialData: [],
    manual: true,
    onSuccess() {
      subzoneIds.value = [];
    },
  });

  watch(
    cityCode,
    () => {
      if (cityCode.value) {
        fetchData({
          city_code: cityCode.value === 'default' ? '' : cityCode.value,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    emits('change');
  };

  defineExpose<Exposes>({
    getValue: () => ({
      city: cityCode.value === 'default' ? '' : cityCode.value,
      subzone_ids: subzoneIds.value,
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
