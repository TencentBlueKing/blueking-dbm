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
    :label="$t('所属业务')"
    property="bk_biz_id"
    required>
    <BusinessSelector
      v-model="state.bizId"
      class="item-input"
      @change="handleChangeBizId" />
  </BkFormItem>
  <BkFormItem
    ref="appAbbrRef"
    :label="$t('业务Code')"
    property="details.db_app_abbr"
    required
    :rules="bkAppAbbrRuels">
    <BkInput
      v-model="state.appAbbr"
      class="item-input"
      :disabled="state.hasEnglishName"
      :placeholder="$t('以小写英文字母开头_且只能包含英文字母_数字_连字符')"
      @input="handleChangeAppAbbr" />
  </BkFormItem>
</template>

<script setup lang="ts">
  import { onMounted } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { getBizs } from '@services/common';
  import type { BizItem } from '@services/types/common';

  import { nameRegx } from '@common/regex';

  import BusinessSelector from '@components/business-selector/BusinessSelector.vue';

  interface Emits {
    (e: 'changeBiz', value: BizItem): void
    (e: 'changeAppAbbr', value: string): void
  }

  const emits = defineEmits<Emits>();
  const bizId = defineModel<number | string>('bizId', {
    required: true,
  });
  const appAbbr = defineModel<string>('appAbbr', {
    default: '',
  });

  const route = useRoute();
  const { t } = useI18n();

  const bkAppAbbrRuels = [
    {
      validator: (val: string) => nameRegx.test(val),
      message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
      trigger: 'change',
    },
  ];

  const state = reactive({
    isLoading: false,
    bizList: [] as BizItem[],
    bizId: null as number | null,
    appAbbr: '',
    hasEnglishName: false,
  });
  const appAbbrRef = ref();

  watch(bizId, (value) => {
    if (typeof value === 'number' || value === null) {
      state.bizId = value;
    } else if (value === '') {
      state.bizId = null;
    }
  }, {
    immediate: true,
  });

  watch(appAbbr, (value) => {
    state.appAbbr = value;
  }, {
    immediate: true,
  });

  // 组件外部：创建业务英文名称后会回写到列表内
  watch(() => state.bizList, () => {
    const info = state.bizList.find(item => state.bizId === item.bk_biz_id);
    state.hasEnglishName = !!info?.english_name;
  }, {
    immediate: true,
    deep: true,
  });

  /**
   * 获取业务列表
   */
  function fetchBizs() {
    state.isLoading = true;
    return getBizs()
      .then((res) => {
        state.bizList = res;
      })
      .finally(() => {
        state.isLoading = false;
      });
  }

  function handleChangeBizId(value: number) {
    bizId.value = value;
    const info = state.bizList.find(item => value === item.bk_biz_id);
    if (info) {
      state.appAbbr = info.english_name;
      handleChangeAppAbbr(state.appAbbr);
      info.english_name && appAbbrRef.value?.clearValidate();
    }
    state.hasEnglishName = !!info?.english_name;
    emits('changeBiz', info || {} as BizItem);
  }

  function handleChangeAppAbbr(value: string) {
    appAbbr.value = value;
    emits('changeAppAbbr', value);
  }

  onMounted(() => {
    fetchBizs()
      .finally(() => {
        if (route.query.bizId) {
          handleChangeBizId(~~route.query.bizId);
        }
      });
  });
</script>
