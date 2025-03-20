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
  <BkFormItem
    class="subzones-form-item"
    :label="t('园区')"
    property="details.sub_zone_ids"
    required
    :rules="rules">
    <BkLoading :loading="loading">
      <BkRadioGroup
        v-if="max === 1"
        v-model="subZone"
        class="subzone-radio-group"
        @change="handleSubZoneChange">
        <BkRadio
          v-for="item in subzoneList"
          :key="item.bk_sub_zone_id"
          :label="item.bk_sub_zone_id">
          {{ item.bk_sub_zone }}
        </BkRadio>
      </BkRadioGroup>
      <div
        v-if="max === 2"
        class="subzone-checkbox-content">
        <BkCheckbox
          v-model="isAllCheck"
          @change="handleCheckAllChange">
          {{ t('随机可用区') }}
        </BkCheckbox>
        <div
          v-if="subzoneList?.length"
          class="subzone-bar" />
        <BkCheckboxGroup
          v-model="subZones"
          v-bk-tooltips="t('至少选择n个区', { n: 2 })"
          class="subzone-checkbox-group"
          @change="handleSubZonesChange">
          <BkCheckbox
            v-for="item in subzoneList"
            :key="item.bk_sub_zone_id"
            :label="item.bk_sub_zone_id">
            {{ item.bk_sub_zone }}
          </BkCheckbox>
        </BkCheckboxGroup>
      </div>
    </BkLoading>
  </BkFormItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getInfrasSubzonesByCity } from '@services/source/infras';

  import { Affinity } from '@common/const';

  interface Props {
    cityCode: string;
    disasterToleranceLevel: string;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<number[]>({
    required: true,
  });

  const { t } = useI18n();

  const isAllCheck = ref(true);
  const subZone = ref<number>(0);
  const subZones = ref([]);

  const rules = [
    {
      required: true,
      trigger: 'change',
      validator: (value: number[]) => {
        const MIN_COUNT = 2;

        if (max.value === 1) {
          return value.length > 0 ? true : Promise.resolve(t('园区不能为空'));
        }

        const hasSubZones = value.length > 0;
        const isSubZonesValid = value.length >= MIN_COUNT;
        const isAllChecked = isAllCheck.value;

        if (hasSubZones && !isSubZonesValid) {
          return Promise.resolve(t('至少选择n个区', { n: MIN_COUNT }));
        }
        if (!hasSubZones && !isAllChecked) {
          return Promise.resolve(t('园区不能为空'));
        }

        return true;
      },
    },
  ];

  const max = computed(() => (props.disasterToleranceLevel === Affinity.CROS_SUBZONE ? 2 : 1));

  const {
    data: subzoneList,
    loading,
    run: runGetInfrasSubzonesByCity,
  } = useRequest(getInfrasSubzonesByCity, {
    manual: true,
  });

  watch(
    () => props.disasterToleranceLevel,
    () => {
      if ([Affinity.CROSS_RACK, Affinity.NONE].includes(props.disasterToleranceLevel as Affinity)) {
        modelValue.value = [];
        subZone.value = 0;
        subZones.value = [];
      }
    },
  );

  watch(
    () => props.cityCode,
    () => {
      if (props.cityCode) {
        runGetInfrasSubzonesByCity({
          city_code: props.cityCode,
        });
      }
      modelValue.value = [];
    },
    {
      immediate: true,
    },
  );

  const handleCheckAllChange = (value: boolean) => {
    if (value) {
      subZones.value = [];
    }
    modelValue.value = [];
  };

  const handleSubZoneChange = () => {
    if (isAllCheck.value) {
      isAllCheck.value = false;
    }
    modelValue.value = [subZone.value];
  };

  const handleSubZonesChange = () => {
    if (isAllCheck.value) {
      isAllCheck.value = false;
    }
    modelValue.value = subZones.value;
  };
</script>

<style lang="less" scoped>
  .subzones-form-item {
    :deep(.bk-radio) {
      position: relative;
      // display: flex;

      & ~ .bk-radio {
        margin-left: 4px;
      }

      &.is-checked {
        .bk-radio-input {
          display: inline-block;

          &::after {
            position: absolute;
            top: 50%;
            left: 50%;
            width: 4px;
            height: 8px;
            border: 2px solid #fff;
            border-top: 0;
            border-left: 0;
            content: '';
            transform: translate(-50%, -60%) scaleY(1) rotate(45deg);
            transform-origin: center;
          }
        }

        .bk-radio-label {
          color: #3a84ff;
          background: #f0f5ff;
        }
      }

      .bk-radio-input {
        position: absolute;
        top: 0;
        left: 0;
        display: none;
        width: 14px;
        height: 14px;
        vertical-align: middle;
        background: var(--primary-color);
        border: 1px solid #979ba5;
        border-color: var(--primary-color);
        border-radius: 2px;
        transition: all 0.1s;
      }

      .bk-radio-label {
        width: 100px;
        margin-left: 0;
        font-size: 12px;
        text-align: center;
        background: #f5f7fa;
        border-radius: 2px;

        &:hover {
          color: #3a84ff;
        }
      }
    }

    .subzone-checkbox-content {
      display: flex;
      align-items: center;

      .subzone-bar {
        width: 1px;
        height: 13px;
        margin: 0 12px;
        border: 1px solid #c4c6cc;
      }

      :deep(.bk-checkbox) {
        position: relative;
        // display: flex;

        & ~ .bk-checkbox {
          margin-left: 4px;
        }

        &.is-checked {
          .bk-checkbox-input {
            display: inline-block;
          }
        }

        .bk-checkbox-input {
          position: absolute;
          top: 0;
          left: 0;
          display: none;
          width: 14px;
          height: 14px;
        }

        .bk-checkbox-label {
          width: 100px;
          margin-left: 0;
          text-align: center;
          background: #f5f7fa;
          border-radius: 2px;

          &:hover {
            color: #3a84ff;
          }
        }
      }
    }
  }
</style>
