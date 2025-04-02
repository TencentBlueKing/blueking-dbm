<template>
  <AppSelect
    :data="withFavorBizList"
    :generate-key="(item: IAppItem) => item.bk_biz_id"
    :generate-name="(item: IAppItem) => item.display_name"
    :search-extension-method="searchExtensionMethod"
    :theme="theme"
    :value="modelValue"
    @change="handleAppChange">
    <template #value="{ data }: { data: IAppItem }">
      <slot
        :data="data"
        name="value">
        <TextOverflowLayout>
          {{ data.name }} (#{{ data.bk_biz_id }} {{ data.english_name ? `, ${data.english_name}` : '' }})
        </TextOverflowLayout>
      </slot>
    </template>
    <template #default="{ data }">
      <AuthTemplate
        v-if="permissionActionId"
        :action-id="permissionActionId"
        :biz-id="data.bk_biz_id"
        :permission="data.permission[permissionActionId]"
        :resource="data.bk_biz_id">
        <template #default="{ permission }">
          <div
            class="db-app-select-item"
            :class="{ 'not-permission': !permission }"
            :data-id="permissionActionId">
            <RenderItem
              v-model:favor-biz-id-map="favorBizIdMap"
              :data="data" />
          </div>
        </template>
      </AuthTemplate>
      <div
        v-else
        class="db-app-select-item">
        <RenderItem
          v-model:favor-biz-id-map="favorBizIdMap"
          :data="data" />
      </div>
    </template>
  </AppSelect>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { computed, shallowRef } from 'vue';

  import AppSelect from '@blueking/app-select';

  import { getBizs } from '@services/source/cmdb';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { encodeRegexp, makeMap } from '@utils';

  import '@blueking/app-select/dist/app-select.css';

  import RenderItem from './RenderItem.vue';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    list: IAppItem[];
    permissionActionId?: string;
    theme?: string;
  }

  type Emits = (e: 'change', value: IAppItem) => void;

  const props = withDefaults(defineProps<Props>(), {
    permissionActionId: 'db_manage',
    theme: 'light',
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    value?: (params: { data: IAppItem }) => VNode;
  }>();

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
</script>
<style lang="less">
  .bk-app-select-menu[data-theme='dark'] {
    .bk-app-select-menu-filter input {
      color: #c4c6cc;
    }

    .bk-app-select-menu-item > span {
      width: 100%;
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
