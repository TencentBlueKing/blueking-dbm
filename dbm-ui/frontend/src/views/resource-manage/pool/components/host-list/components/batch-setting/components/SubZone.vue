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
  <DbSelect
    v-model="modelValue"
    filterable
    :loading="isLoading"
    :placeholder="t('请选择园区')">
    <DbOption
      v-for="item in optionList"
      :key="item.bk_sub_zone_id"
      :label="item.bk_sub_zone"
      :value="item.bk_sub_zone_id">
    </DbOption>
  </DbSelect>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasSubzonesByCity } from '@services/source/infras';

  interface Props {
    formData: {
      bk_cloud_region: string;
      bk_cloud_zone: string;
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

  // 层级限制：园区候选按已选 云区域 → 城市 → 云可用区 逐层过滤（园区归属数据自带各层字段）
  const optionList = computed(() => {
    let list = subzoneList.value || [];
    if (props.formData.bk_cloud_region) {
      list = list.filter((item) => item.bk_cloud_region === props.formData.bk_cloud_region);
    }
    if (props.formData.city_meta) {
      // city_meta 存城市代码（City 组件的选中值），与园区归属数据的 bk_city_code 同域
      list = list.filter((item) => item.bk_city_code === props.formData.city_meta);
    }
    if (props.formData.bk_cloud_zone) {
      list = list.filter((item) => item.bk_cloud_zone === props.formData.bk_cloud_zone);
    }
    return list;
  });

  watch(
    () => [props.formData.bk_cloud_region, props.formData.city_meta, props.formData.bk_cloud_zone],
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
