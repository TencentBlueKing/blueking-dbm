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
  <BkSelect
    v-model="modelValue"
    filterable
    :loading="isLoading"
    :placeholder="t('请选择园区')">
    <BkOption
      v-for="item in optionList"
      :key="item.bk_sub_zone_id"
      :label="item.bk_sub_zone"
      :value="item.bk_sub_zone_id">
    </BkOption>
  </BkSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasSubzonesByCity } from '@services/source/infras';

  interface Props {
    formData: {
      city_meta: string;
    };
  }

  interface Expose {
    getValue: () =>
      | {
          sub_zone_meta: {
            sub_zone: string;
            sub_zone_id: string;
          };
        }
      | undefined;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const { data: subzoneList, loading: isLoading } = useRequest(getInfrasSubzonesByCity);

  const optionList = computed(() => {
    if (props.formData.city_meta) {
      return (subzoneList.value || []).filter(
        (subzoneItem) => subzoneItem.bk_city === Number(props.formData.city_meta),
      );
    }
    return subzoneList.value;
  });

  watch(
    () => props.formData.city_meta,
    () => {
      modelValue.value = '';
    },
  );

  defineExpose<Expose>({
    getValue() {
      if (!modelValue.value) {
        return;
      }
      return {
        sub_zone_meta: {
          sub_zone: (optionList.value || []).find((item) => item.bk_sub_zone_id === Number(modelValue.value))!
            .bk_sub_zone,
          sub_zone_id: String(modelValue.value),
        },
      };
    },
  });
</script>
