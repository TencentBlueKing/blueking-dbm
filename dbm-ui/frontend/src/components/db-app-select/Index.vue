<template>
  <AppSelect
    v-bind="{ ...attrs, ...props }"
    :data="withFavorBizList"
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

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { encodeRegexp, makeMap } from '@utils';

  import '@blueking/app-select/dist/style.css';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    list: IAppItem[];
  }

  type Emits = (e: 'change', value?: IAppItem) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  defineSlots<{
    value?: (params: { data: IAppItem }) => VNode;
  }>();

  const modelValue = defineModel<IAppItem>();

  const attrs = useAttrs();
  const userProfile = useUserProfile();

  const favorBizIdMap = makeMap(userProfile.profile[UserPersonalSettings.APP_FAVOR] || []);

  const withFavorBizList = computed(() => _.sortBy(props.list, (item) => favorBizIdMap[item.bk_biz_id]));

  const searchExtensionMethod = (data: IAppItem, keyword: string) => {
    const rule = new RegExp(encodeRegexp(keyword), 'i');

    return rule.test(data.english_name);
  };

  const handleAppChange = (appInfo?: IAppItem) => {
    modelValue.value = appInfo;
    emits('change', appInfo);
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
      & span {
        display: inline !important;
      }
    }
  }
</style>
