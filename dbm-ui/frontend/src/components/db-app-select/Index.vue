<template>
  <AppSelect
    :data="withFavorBizList"
    :generate-key="(item: IAppItem) => item.bk_biz_id"
    :generate-name="(item: IAppItem) => item.display_name"
    :search-extension-method="searchExtensionMethod"
    :theme="theme"
    :value="modelValue"
    @change="handleAppChange">
    <template #value="{ data }">
      <div>
        <span>{{ data.name }}</span>
        <span> (#{{ data.bk_biz_id }}</span>
        <template v-if="data.english_name">, {{ data.english_name }}</template>
        <span>)</span>
      </div>
    </template>
    <template #default="{ data }">
      <AuthTemplate
        :action-id="permissionActionId"
        :biz-id="data.bk_biz_id"
        :permission="data.permission[permissionActionId]"
        :resource="data.bk_biz_id"
        style="flex: 1">
        <template #default="{ permission }">
          <div
            class="db-app-select-item"
            :class="{ 'not-permission': !permission }"
            :data-id="permissionActionId">
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

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import { encodeRegexp, makeMap } from '@utils';

  import AppSelect from '@blueking/app-select';

  import RenderItem from './RenderItem.vue';

  import '@blueking/app-select/dist/style.css';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    theme?: string;
    permissionActionId?: string;
    list: IAppItem[];
  }
  interface Emits {
    (e: 'change', value: IAppItem): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    theme: 'light',
    permissionActionId: 'db_manage',
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IAppItem>();

  const userProfile = useUserProfile();

  const favorBizIdMap = shallowRef(makeMap(userProfile.profile[UserPersonalSettings.APP_FAVOR] || []));

  const withFavorBizList = computed(() => _.sortBy(props.list, (item) => favorBizIdMap.value[item.bk_biz_id]));

  const searchExtensionMethod = (data: IAppItem, keyword: string) => {
    const rule = new RegExp(encodeRegexp(keyword), 'i');

    return rule.test(data.english_name);
  };

  const handleAppChange = (appInfo: IAppItem) => {
    modelValue.value = appInfo;
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
  .bk-app-select-menu[data-theme='dark'] {
    .bk-app-select-menu-filter input {
      color: #c4c6cc;
    }

    .not-permission {
      * {
        color: #70737a !important;
      }

      .db-app-select-name {
        color: #c4c6cc;
      }
    }
  }

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
    }

    .db-app-select-desc {
      display: flex;
      overflow: hidden;
      color: #979ba5;
      white-space: nowrap;
    }

    .db-app-select-en-name {
      overflow: hidden;
      text-overflow: ellipsis;
      flex: 0 1 auto;
    }
  }

  .db-app-select-tooltips {
    z-index: 1000000 !important;
    white-space: nowrap;
  }

  .tippy-box[data-theme='bk-app-select-menu'] {
    border: none !important;
    box-shadow: 0 2px 3px 0 rgb(0 0 0 / 10%) !important;
  }
</style>
