<template>
  <AppSelect
    v-model="modelValue"
    :data="withFavorBizList"
    :generate-key="(item: IAppItem) => item.bk_biz_id"
    :generate-name="(item: IAppItem) => item.display_name"
    :search-extension-method="searchExtensionMethod"
    :theme="theme"
    @change="handleAppChange">
    <template #value="{ data }">
      <div>
        {{ data.name }} (#{{ data.bk_biz_id }}
        <template v-if="data.english_name">, {{ data.english_name }}</template>
        )
      </div>
    </template>
    <template #default="{ data }">
      <AuthTemplate
        action-id="db_manage"
        :permission="data.permission.db_manage"
        :resource="data.bk_biz_id"
        style="flex: 1">
        <template #default="{ permission }">
          <div
            class="db-app-select-item"
            :class="{ 'not-permission': !permission }">
            <RenderItem :data="data" />
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
        </template>
      </AuthTemplate>
    </template>
  </AppSelect>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, shallowRef } from 'vue';

  import { getBizs } from '@services/source/cmdb';

  import { useGlobalBizs, useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import { encodeRegexp, makeMap } from '@utils';

  import AppSelect from '@blueking/app-select';

  import RenderItem from './RenderItem.vue';

  import '@blueking/app-select/dist/style.css';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    theme: string;
  }
  interface Emits {
    (e: 'change', value: IAppItem): void;
  }

  defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IAppItem>();

  const userProfile = useUserProfile();

  const { bizs: bizList } = useGlobalBizs();

  const favorBizIdMap = shallowRef(makeMap(userProfile.profile[UserPersonalSettings.APP_FAVOR] || []));

  const withFavorBizList = computed(() => _.sortBy(bizList, (item) => favorBizIdMap.value[item.bk_biz_id]));

  const searchExtensionMethod = (data: IAppItem, keyword: string) => {
    const rule = new RegExp(encodeRegexp(keyword), 'i');

    return rule.test(data.english_name);
  };

  const handleAppChange = (appInfo: IAppItem) => {
    emits('change', appInfo);
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
<style lang="less">
  .db-app-select-item {
    display: flex;
    align-items: center;
    width: 100%;
    user-select: none;

    &:hover {
      .favor-btn {
        opacity: 100%;
      }
    }

    &.not-permission {
      * {
        color: #70737a !important;
      }
    }

    .favor-btn {
      opacity: 0%;
      transition: all 0.1s;
    }

    .db-app-select-text {
      display: flex;
      flex: 1;
      padding-right: 12px;
      overflow: hidden;
    }
    .db-app-select-name {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      color: #c4c6cc;
    }
    .db-app-select-desc {
      display: flex;
      white-space: nowrap;
      color: #979ba5;
      overflow: hidden;
    }
    .db-app-select-en-name {
      flex: 0 1 auto;
      text-overflow: ellipsis;
      overflow: hidden;
    }
    .favor-btn {
      opacity: 0%;
      transition: all 0.1s;
    }
  }
  .db-app-select-tooltips {
    white-space: nowrap;
    z-index: 1000000 !important;
  }

  .tippy-box[data-theme='bk-app-select-menu'] {
    border: none !important;
    box-shadow: 0 2px 3px 0 rgb(0 0 0 / 10%) !important;
  }
</style>
