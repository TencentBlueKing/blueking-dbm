<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkComposeFormItem class="search-city-subzones">
    <BkSelect
      v-model="cityCode"
      clearable
      style="width: 100px"
      @change="handleCityChange">
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
        v-for="item in filterSubzoneList"
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
    model: Record<string, any>;
  }

  interface Emits {
    (e: 'change', value: any, name?: string): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const cityCode = defineModel<string>({
    default: '',
  });

  defineOptions({
    inheritAttrs: false,
  });

  const subzoneIds = ref<string[]>([]);
  const citiyList = ref<CityItem[]>([]);

  const filterSubzoneList = computed(() =>
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
      if (props.model) {
        cityCode.value = props.model.city;
        subzoneIds.value = props.model.subzone_ids;
      }
    },
    {
      immediate: true,
    },
  );

  const handleCityChange = (value: string) => {
    subzoneIds.value = [];
    emits('change', value);
  };

  const handleChange = (value: string[]) => {
    emits('change', value, 'subzone_ids');
  };
</script>
<style lang="less" scoped>
  .search-city-subzones {
    display: flex;
    width: 100%;

    :deep(.bk-compose-form-item-tail) {
      flex: 1;
    }
  }
</style>
