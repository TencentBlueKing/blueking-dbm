<template>
  <AppSelect
    v-bind="{ ...attrs, ...props }"
    :data="dataList"
    :generate-key="(item: IAppItem) => item.bk_biz_id"
    :generate-name="(item: IAppItem) => item.display_name"
    :search-extension-method="searchExtensionMethod"
    :value="modelValue"
    @change="handleAppChange">
    <template #value="{ data }">
      <slot
        :data="data"
        name="value">
        <TextOverflowLayout class="db-select-no-permission-trigger">
          <span>{{ data.name }}</span>
          <span> (#{{ data.bk_biz_id }}</span>
          <span v-if="data.english_name">, {{ data.english_name }}</span>
          <span>)</span>
        </TextOverflowLayout>
      </slot>
    </template>
    <template #default="{ data }">
      <TextOverflowLayout class="db-select-no-permission-item">
        <span>{{ data.name }}</span>
        <span style="color: #979ba5">
          (#{{ data.bk_biz_id }}{{ data.english_name ? `, ${data.english_name}` : '' }})
        </span>
        <template
          v-if="data.bk_biz_id !== publicBiz.bk_biz_id"
          #append>
          <DbIcon
            v-if="favorBizIdMap[data.bk_biz_id]"
            class="unfavor-btn ml-4"
            style="color: #ffb848"
            type="star-fill"
            @click.stop="handleUnfavor(data.bk_biz_id)" />
          <DbIcon
            v-else
            class="favor-btn ml-4"
            type="star"
            @click.stop="handleFavor(data.bk_biz_id)" />
        </template>
      </TextOverflowLayout>
    </template>
  </AppSelect>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { computed } from 'vue';

  import AppSelect from '@blueking/app-select';

  import { getBizs } from '@services/source/cmdb';

  import { useGlobalBizs, useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { encodeRegexp, makeMap } from '@utils';

  import '@blueking/app-select/dist/style.css';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    list: IAppItem[];
    showPublicBiz?: boolean;
  }

  type Emits = (e: 'change', value?: IAppItem) => void;

  const props = withDefaults(defineProps<Props>(), {
    showPublicBiz: true,
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    value?: (params: { data: IAppItem }) => VNode;
  }>();

  const modelValue = defineModel<IAppItem>();

  const attrs = useAttrs();
  const userProfile = useUserProfile();
  const { publicBiz } = useGlobalBizs();

  const favorBizIdMap = shallowRef(makeMap(userProfile.profile[UserPersonalSettings.APP_FAVOR] || []));

  const dataList = computed(() => {
    const sortedList = _.sortBy(props.list, (item) => favorBizIdMap.value[item.bk_biz_id]);

    if (props.showPublicBiz) {
      sortedList.unshift(publicBiz);
    }
    return sortedList;
  });

  const searchExtensionMethod = (data: IAppItem, keyword: string) => {
    const rule = new RegExp(encodeRegexp(keyword), 'i');

    return rule.test(data.english_name);
  };

  const handleAppChange = (appInfo?: IAppItem) => {
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
  .bk-app-select-value {
    .db-select-no-permission-trigger {
      padding-right: 12px;

      & span {
        display: inline !important;
      }
    }
  }

  .tippy-box[data-theme='bk-app-select-menu'] {
    .db-select-no-permission-item {
      width: 100%;

      .layout-content {
        width: 100%;
      }

      & span {
        display: inline !important;
      }

      &:hover {
        .favor-btn {
          opacity: 100%;
        }
      }

      .favor-btn {
        opacity: 0%;
        transition: all 0.1s;
      }
    }
  }
</style>
