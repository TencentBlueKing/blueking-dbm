<template>
  <BkCollapsePanel :name="currentConfig.id">
    <div class="toolbox-side-header">
      <DbIcon
        class="toolbox-side-status"
        type="down-shape" />
      <i
        class="toolbox-side-icon"
        :class="currentConfig.icon" />
      <span
        v-overflow-tips
        class="toolbox-side-title text-overflow">
        {{ currentConfig.name }}
      </span>
      <span
        v-if="draggable"
        class="toolbox-side-drag"
        @click.stop />
    </div>
    <template #content>
      <div class="toolbox-side-content">
        <template
          v-for="item of currentConfig.children"
          :key="item.id">
          <div
            class="toolbox-side-item"
            :class="{
              'toolbox-side-item--active': item.id === activeViewName
            }"
            @click="handleRouterChange(item.id)">
            <div class="toolbox-side-left">
              <span
                v-overflow-tips
                class="text-overflow">
                {{ item.name }}
              </span>
              <TaskCount
                v-if="item.id === 'MySQLExecute'"
                class="count" />
            </div>
            <DbIcon
              v-bk-tooltips="favorMap[item.id] ? t('从导航移除') : t('收藏至导航')"
              class="toolbox-side-favor"
              :type="favorMap[item.id] ? 'star-fill' : 'star'"
              @click.stop="handleRouterFavor(item.id)" />
          </div>
        </template>
      </div>
    </template>
  </BkCollapsePanel>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import MenuConfig from '@views/spider-manage/toolbox-menu';

  import { messageSuccess } from '@utils';

  import TaskCount from './TaskCount.vue';

  interface Props {
    id: string,
    draggable: boolean,
    activeViewName: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();
  const userProfileStore = useUserProfile();
  const eventBus = useEventBus();

  const favorMap = defineModel<Record<string, boolean>>('favorMap', {
    required: true,
  });

  const currentConfig = _.find(MenuConfig, item => item.id === props.id) as (typeof MenuConfig)[number];

  const handleRouterChange = (routerName: string) => {
    router.push({
      name: routerName,
    });
  };

  const handleRouterFavor = (routerName: string) => {
    const lastFavorMap = { ...favorMap.value };
    let successMessage = '';
    if (lastFavorMap[routerName]) {
      delete lastFavorMap[routerName];
      successMessage = t('取消收藏成功');
    } else {
      lastFavorMap[routerName] = true;
      successMessage = t('收藏成功');
    }
    userProfileStore.updateProfile({
      label: UserPersonalSettings.SPIDER_TOOLBOX_FAVOR,
      values: Object.keys(lastFavorMap),
    }).then(() => {
      messageSuccess(successMessage);
      favorMap.value = lastFavorMap;
      eventBus.emit('SPIDER_TOOLBOX_CHANGE');
    });
  };
</script>

