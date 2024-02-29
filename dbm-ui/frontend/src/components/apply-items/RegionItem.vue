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
  <DbCard :title="$t('地域要求')">
    <BkLoading :loading="state.isLoading">
      <BkFormItem
        :label="$t('数据库部署地域')"
        property="details.city_code"
        required>
        <BkRadioGroup
          v-if="state.regions.length > 0"
          v-model="state.cityCode"
          class="region-group"
          @change="handleChange">
          <div
            v-for="info of state.regions"
            :key="info.city_code"
            class="region-group__item">
            <BkRadioButton
              class="region-group__badge"
              :class="[
                {
                  'region-group__badge--tight': info.inventory_tag === 'insufficient',
                },
              ]"
              :data-tag="getCitiyTag(info)"
              :label="info.city_code">
              {{ info.city_name }}
            </BkRadioButton>
          </div>
        </BkRadioGroup>
        <span class="region-tips">{{ $t('如果对请求延时有要求_请尽量选择靠近接入点的地域') }}</span>
      </BkFormItem>
    </BkLoading>
  </DbCard>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getInfrasCities } from '@services/source/infras';

  type CityItem = ServiceReturnType<typeof getInfrasCities>;

  interface Emits {
    (e: 'change', value: string): void;
  }

  interface Expose {
    getValue: () => { cityCode: string; cityName: string };
  }

  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  enum Inventory {
    INSUFFICIENT = '紧张',
    SUFFICIENT = '充足',
  }
  type InventoryStrings = keyof typeof Inventory;

  const state = reactive({
    isLoading: false,
    regions: [] as CityItem,
    cityCode: modelValue.value,
    cityName: '' as string | undefined,
  });

  watch(modelValue, () => {
    state.cityCode = modelValue.value;
  });

  /**
   * 获取服务器资源的城市信息
   */
  function fetchInfrasCities() {
    getInfrasCities()
      .then((res) => {
        state.regions = res || [];
        // 默认选中第一个
        const [firstRegion] = state.regions;
        if (firstRegion) {
          state.cityCode = firstRegion.city_code;
          handleChange(firstRegion.city_code);
        }
      })
      .finally(() => {
        state.isLoading = false;
      });
  }
  fetchInfrasCities();

  /**
   * 获取区域存货标签
   */
  function getCitiyTag(info: CityItem[number]) {
    return t(Inventory[info.inventory_tag.toLocaleUpperCase() as InventoryStrings]);
  }

  function handleChange(value: string) {
    modelValue.value = value;
    state.cityName = state.regions.find((item) => item.city_code === value)?.city_name;
    emits('change', value);
  }

  defineExpose<Expose>({
    getValue() {
      return {
        cityCode: state.cityCode,
        cityName: state.cityCode,
      };
    },
  });
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .region-group {
    .flex-center();

    :deep(.bk-radio-button-label) {
      min-width: 100px;
      border-radius: 0;
    }

    &__item {
      position: relative;
      margin-left: -1px;
    }

    &__region {
      position: absolute;
      top: -21px;
      left: 50%;
      z-index: 2;
      width: 60px;
      font-size: @font-size-mini;
      line-height: normal;
      color: @gray-color;
      text-align: center;
      background-color: @white-color;
      transform: translateX(-50%);
    }

    &__badge {
      position: relative;

      &::after {
        position: absolute;
        top: -8px;
        right: 0;
        z-index: 10;
        height: 32px;
        padding: 0 6px 0 10px;
        font-size: 20px;
        line-height: 32px;
        color: #fff;
        background-color: @bg-success;
        border-radius: 0 0 0 12px;
        content: attr(data-tag);
        transform: scale(0.5) translateX(50%);
      }

      &--tight {
        &::after {
          background-color: @bg-warning;
        }
      }
    }
  }

  .region-tips {
    font-size: @font-size-mini;
    line-height: normal;
    color: @gray-color;
  }
</style>
