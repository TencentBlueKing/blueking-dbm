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
    class="spec-operation-biz-scope-item"
    :label="t('应用范围')"
    property="biz_scope"
    required
    :rules="rules">
    <div
      v-bk-tooltips="{
        content: t('该规格已被使用，不允许修改'),
        disabled: editable,
      }"
      class="biz-scope-container">
      <BkRadioGroup
        v-model="bizScope"
        class="biz-scope-option"
        :disabled="!editable"
        @change="handleBizScopeChange">
        <BkRadio
          class="biz-scope-item"
          :label="BizScopes.ALL">
          <DbIcon
            svg
            :type="BizScopesInfoMap[BizScopes.ALL].icon" />
          <span class="ml-4">{{ BizScopesInfoMap[BizScopes.ALL].label }}</span>
        </BkRadio>
        <BkRadio
          class="biz-scope-item"
          :label="BizScopes.BIZ">
          <DbIcon
            svg
            :type="BizScopesInfoMap[BizScopes.BIZ].icon" />
          <span class="ml-4">{{ BizScopesInfoMap[BizScopes.BIZ].label }}</span>
        </BkRadio>
      </BkRadioGroup>
      <BizSelector
        v-if="bizScope === BizScopes.BIZ"
        v-model="selectedBiz"
        class="ml-44 mt-34"
        :disabled="!editable"
        style="flex: 1"
        @change="handleSelectedBizChange" />
    </div>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { BizScopes, BizScopesInfoMap } from '../../../consts/bizScope';
  import BizSelector from '../../common/BizSelector.vue';

  interface Props {
    data: number[];
    editable: boolean;
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    getValue: () => number[];
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const rules = [
    {
      message: t('指定业务不能为空'),
      required: true,
      validator: () => {
        if (bizScope.value === BizScopes.BIZ) {
          return selectedBiz.value.length > 0;
        }
        return true;
      },
    },
  ];

  const selectedBiz = ref(props.data.map((item) => `${item}`));
  const bizScope = ref(selectedBiz.value.length === 0 ? BizScopes.ALL : BizScopes.BIZ);

  const handleBizScopeChange = () => {
    selectedBiz.value = [];
    emits('change');
  };

  const handleSelectedBizChange = () => {
    emits('change');
  };

  defineExpose<Exposes>({
    getValue: () => selectedBiz.value.map((item) => Number(item)),
  });
</script>

<style lang="less">
  .spec-operation-biz-scope-item {
    .biz-scope-container {
      display: flex;

      .biz-scope-option {
        display: flex;
        flex-direction: column;

        .biz-scope-item {
          width: fit-content;
          margin-left: 0;

          .bk-radio-label {
            display: flex;
            margin-left: 8px;
            align-items: center;

            .db-svg-icon {
              font-size: 20px;
            }
          }
        }
      }
    }
  }
</style>
