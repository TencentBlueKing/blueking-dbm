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
    :label="t('所属业务')"
    property="bk_biz_id"
    required>
    <BkLoading
      :loading="isBizLoading"
      style="width: 435px">
      <DbAppSelect
        :list="bizList"
        :model-value="currentBiz"
        :permission-action-id="perrmisionActionId"
        @change="handleAppChange">
      </DbAppSelect>
    </BkLoading>
  </BkFormItem>
  <BkFormItem
    ref="appAbbrRef"
    :label="t('业务Code')"
    property="details.db_app_abbr"
    required
    :rules="bkAppAbbrRuels">
    <BkInput
      v-model="appAbbr"
      v-bk-tooltips="{
        trigger: 'click',
        placement: 'top',
        theme: 'light',
        content: dbAppAbbrPlaceholder,
      }"
      class="item-input"
      :disabled="hasEnglishName"
      :placeholder="dbAppAbbrPlaceholder"
      @input="handleChangeAppAbbr" />
  </BkFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getBizs } from '@services/source/cmdb';
  import type { BizItem } from '@services/types';

  import { nameRegx } from '@common/regex';

  import DbAppSelect from '@components/db-app-select/Index.vue';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    perrmisionActionId: string;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  interface Emits {
    (e: 'changeBiz', value: BizItem): void;
    (e: 'changeAppAbbr', value: string): void;
  }

  const bizId = defineModel<number | string>('bizId', {
    required: true,
  });
  const appAbbr = defineModel<string>('appAbbr', {
    default: '',
  });

  const { t } = useI18n();

  const route = useRoute();

  const currentBiz = shallowRef<IAppItem>();
  const bizList = shallowRef<IAppItem[]>([]);
  const hasEnglishName = ref(false);
  const appAbbrRef = ref();

  const dbAppAbbrPlaceholder = t('以小写英文字母开头_且只能包含英文字母_数字_连字符');

  const { loading: isBizLoading } = useRequest(getBizs, {
    defaultParams: [
      {
        action: props.perrmisionActionId,
      },
    ],
    onSuccess(data) {
      bizList.value = data;
    },
  });

  const bkAppAbbrRuels = [
    {
      validator: (val: string) => nameRegx.test(val),
      message: dbAppAbbrPlaceholder,
      trigger: 'change',
    },
    {
      validator: (val: string) => {
        if (hasEnglishName.value || val === '') {
          return true;
        }
        return !bizList.value!.find((item) => item.english_name === val);
      },
      message: t('业务code不允许重复'),
      trigger: 'blur',
    },
  ];

  watch(
    route,
    () => {
      const currentBiz = Number(route.query.bizId);
      if (currentBiz > 0) {
        bizId.value = currentBiz;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [bizId.value, bizList.value],
    () => {
      currentBiz.value = _.find(bizList.value, (item) => item.bk_biz_id === bizId.value);
      const englishName = currentBiz.value?.english_name;
      hasEnglishName.value = !!englishName;
      appAbbr.value = englishName ?? '';
      // 从申请实例 跳转过来，需要同步数据出去
      if (route.query.bizId && currentBiz.value) {
        handleAppChange(currentBiz.value);
      }
    },
    {
      immediate: true,
    },
  );

  const handleChangeAppAbbr = (value: string) => {
    appAbbr.value = value;
    emits('changeAppAbbr', value);
  };

  const handleAppChange = (appInfo: IAppItem) => {
    handleChangeAppAbbr(appInfo.english_name);
    hasEnglishName.value = !!appInfo?.english_name;
    appInfo.english_name && appAbbrRef.value?.clearValidate();

    bizId.value = appInfo.bk_biz_id;
    emits('changeBiz', { ...appInfo });
  };
</script>
