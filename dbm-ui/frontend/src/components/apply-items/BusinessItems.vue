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
    <AppSelect
      :data="withFavorBizList"
      :generate-key="(item: IAppItem) => item.bk_biz_id"
      :generate-name="(item: IAppItem) => item.display_name"
      style="width: 435px"
      :value="currentBiz"
      @change="handleAppChange">
      <template #default="{ data }">
        <AuthTemplate
          :action-id="perrmisionActionId"
          :biz-id="data.bk_biz_id"
          :permission="data.permission.db_manage"
          :resource="data.bk_biz_id"
          style="width: 100%">
          <div class="db-app-select-item">
            <div>{{ data.name }} (#{{ data.bk_biz_id }})</div>
            <div style="margin-left: auto">
              <DbIcon
                v-if="favorBizIdMap[data.bk_biz_id]"
                class="unfavor-btn"
                style="color: #ffb848"
                type="star-fill"
                @click.stop="handleUnfavor(data.bk_biz_id)" />
              <DbIcon
                v-else
                class="favor-btn"
                type="star"
                @click.stop="handleFavor(data.bk_biz_id)" />
            </div>
          </div>
        </AuthTemplate>
      </template>
    </AppSelect>
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
  import { useRoute } from 'vue-router';

  import { getBizs } from '@services/source/cmdb';
  import type { BizItem } from '@services/types';

  import { useGlobalBizs, useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';
  import { nameRegx } from '@common/regex';

  import { makeMap } from '@utils';

  import AppSelect from '@blueking/app-select';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    perrmisionActionId: string;
  }

  defineProps<Props>();

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
  const { bizs: bizList } = useGlobalBizs();
  const userProfile = useUserProfile();

  const currentBiz = shallowRef<IAppItem>();
  const favorBizIdMap = shallowRef(makeMap(userProfile.profile[UserPersonalSettings.APP_FAVOR] || []));
  const hasEnglishName = ref(false);

  const withFavorBizList = computed(() => _.sortBy(bizList, (item) => favorBizIdMap.value[item.bk_biz_id]));

  const dbAppAbbrPlaceholder = t('以小写英文字母开头_且只能包含英文字母_数字_连字符');

  const bkAppAbbrRuels = [
    {
      validator: (val: string) => nameRegx.test(val),
      message: dbAppAbbrPlaceholder,
      trigger: 'change',
    },
  ];

  const appAbbrRef = ref();

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
    bizId,
    () => {
      currentBiz.value = _.find(bizList, (item) => item.bk_biz_id === bizId.value);
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

  const handleUnfavor = (bizId: number) => {
    const lastFavorBizIdMap = { ...favorBizIdMap.value };
    delete lastFavorBizIdMap[bizId];
    favorBizIdMap.value = lastFavorBizIdMap;

    userProfile.updateProfile({
      label: UserPersonalSettings.APP_FAVOR,
      values: Object.keys(lastFavorBizIdMap),
    });
  };

  const handleFavor = (bizId: number) => {
    favorBizIdMap.value = {
      ...favorBizIdMap.value,
      [bizId]: true,
    };
    userProfile.updateProfile({
      label: UserPersonalSettings.APP_FAVOR,
      values: Object.keys(favorBizIdMap.value),
    });
  };
</script>
