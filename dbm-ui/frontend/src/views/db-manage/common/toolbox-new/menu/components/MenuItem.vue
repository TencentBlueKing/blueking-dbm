<template>
  <div
    v-db-console="data.dbConsoleValue"
    class="toolbox-menu-item"
    @click="handleRouterChange">
    <div class="toolbox-menu-item-content">
      <div class="tool-item-name">
        {{ data.name }}
        <BkTag
          v-if="data.isFix"
          class="tool-item-tag ml-4"
          size="small"
          theme="warning">
          {{ t('故障修复') }}
        </BkTag>
      </div>
      <BkOverflowTitle
        class="tool-item-desc"
        type="tips">
        {{ data.desc }}
      </BkOverflowTitle>
    </div>
    <DbIcon
      v-bk-tooltips="favorMap[data.id] ? t('取消收藏') : t('添加收藏')"
      class="toolbox-side-favor"
      :type="favorMap[data.id] ? 'star-fill' : 'star'"
      @click.stop="handleRouterFavor()" />
  </div>
</template>

<script setup lang="ts">
  import { storeToRefs } from 'pinia';
  import { useI18n } from 'vue-i18n';

  import { useUserProfile } from '@stores';

  import { DBTypes, toolboxProfileKeyMap } from '@common/const';

  import { makeMap, messageSuccess, messageWarn } from '@utils';

  import type { ToolboxLeafNode } from '../../common/types';

  interface Props {
    data: ToolboxLeafNode;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const profileStore = useUserProfile();
  const { profile } = storeToRefs(profileStore);

  const profileFavorKey = toolboxProfileKeyMap[route.meta.dbType as DBTypes]!.favor;

  const favorMap = computed(() => {
    return makeMap(profile.value[profileFavorKey] || []);
  });

  const handleRouterChange = () => {
    router.push({
      name: props.data.id,
    });
  };

  const handleRouterFavor = () => {
    const routerName = props.data.id;
    const lastFavorMap = { ...favorMap.value };
    let lastFavor = profile.value[profileFavorKey] || [];
    let successMessage = '';
    if (lastFavorMap[routerName]) {
      lastFavor = (profile.value[profileFavorKey] || []).filter((item: string) => item !== routerName);
      successMessage = t('取消收藏成功');
    } else {
      if (lastFavor.length >= 12) {
        messageWarn(t('最多收藏n个工具，请先取消部分收藏', { n: 12 }));
        return;
      }
      lastFavor.unshift(routerName);
      successMessage = t('添加收藏成功');
    }
    profileStore
      .updateProfile({
        label: profileFavorKey,
        values: lastFavor,
      })
      .then(() => {
        messageSuccess(successMessage);
      });
  };
</script>

<style lang="less">
  .toolbox-menu-item {
    display: inline-flex;
    align-items: center;
    width: calc((100% - 12px * (6 - 1)) / 6);
    padding: 8px 18px;
    cursor: pointer;
    background-color: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 4px 0 #1919290d;

    &:hover {
      box-shadow: 0 2px 4px 0 #0000001a;

      .toolbox-side-favor {
        display: block;
      }
    }

    .toolbox-menu-item-content {
      flex: 1;
      min-width: 0;
      overflow: hidden;
    }

    .tool-item-name {
      display: flex;
      align-items: center;
      font-size: 12px;
      font-weight: bolder;
      color: #4d4f56;
    }

    .tool-item-desc {
      font-size: 12px;
      color: #979ba5;
    }

    .toolbox-side-favor {
      display: none;
      margin-left: auto;

      &.db-icon-star-fill {
        display: block;
        color: @warning-color;
      }
    }
  }
</style>
