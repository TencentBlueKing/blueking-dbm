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
    :label="t('容灾要求')"
    property="details.disaster_tolerance_level"
    required>
    <BkRadioGroup v-model="modelValue">
      <BkRadio
        v-for="item in affinityList"
        :key="item.value"
        :label="item.value">
        {{ item.label }}
      </BkRadio>
    </BkRadioGroup>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { Affinity, affinityMap } from '@common/const';

  import { checkDbConsole } from '@utils';

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const getAffinityItem = (key: Affinity) => {
    return {
      label: affinityMap[key],
      value: key,
    };
  };

  const affinityList = [Affinity.CROS_SUBZONE, Affinity.SAME_SUBZONE_CROSS_SWTICH, Affinity.CROSS_RACK].map((key) =>
    getAffinityItem(key),
  );

  if (checkDbConsole('common.affinityNone')) {
    affinityList.push(getAffinityItem(Affinity.NONE));
  }
</script>
