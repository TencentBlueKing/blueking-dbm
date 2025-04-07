<template>
  <TextOverflowLayout class="db-app-select-render-item">
    <div class="db-app-select-content">
      <span class="db-app-select-name">
        {{ data.name }}
      </span>
      <span style="color: #979ba5">
        (#{{ data.bk_biz_id }}{{ data.english_name ? `, ${data.english_name}` : '' }})
      </span>
    </div>
    <template #append>
      <DbIcon
        v-if="favorBizIdMap[data.bk_biz_id]"
        class="ml-4"
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

<script setup lang="ts">
  import { getBizs } from '@services/source/cmdb';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  type IAppItem = ServiceReturnType<typeof getBizs>[number];

  interface Props {
    data: IAppItem;
  }

  defineProps<Props>();

  const favorBizIdMap = defineModel<Record<string | number, boolean>>('favorBizIdMap', {
    required: true,
  });

  const userProfile = useUserProfile();

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
    nextTick(() => {
      userProfile.updateProfile({
        label: UserPersonalSettings.APP_FAVOR,
        values: Object.keys(favorBizIdMap.value),
      });
    });
  };
</script>

<style lang="less" scoped>
  .db-app-select-render-item {
    width: 100%;

    :deep(.layout-content) {
      width: 100%;
    }

    .db-app-select-content > span {
      display: inline !important;
    }

    .db-app-select-name {
      flex: 1;
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
</style>
