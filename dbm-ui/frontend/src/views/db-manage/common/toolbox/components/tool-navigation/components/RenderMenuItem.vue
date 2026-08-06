<template>
  <BkCollapsePanel :name="data.id">
    <div class="toolbox-side-header">
      <DbIcon
        class="toolbox-side-status"
        type="down-shape" />
      <i
        class="toolbox-side-icon"
        :class="data.icon" />
      <span
        v-overflow-tips
        class="toolbox-side-title text-overflow">
        {{ data.name }}
      </span>
      <span
        class="toolbox-side-drag"
        @click.stop />
    </div>
    <template #content>
      <div class="toolbox-side-content">
        <template
          v-for="item of data.children"
          :key="item.id">
          <div
            v-db-console="item.dbConsoleValue"
            class="toolbox-side-item"
            :class="{
              'toolbox-side-item--active': item.id === activeViewName,
            }"
            @click="handleRouterChange(item.id)">
            <div class="toolbox-side-left">
              <span
                v-overflow-tips
                class="text-overflow">
                {{ item.name }}
              </span>
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
  import { storeToRefs } from 'pinia';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { DBTypes, toolboxProfileKeyMap } from '@common/const';

  import { makeMap, messageSuccess } from '@utils';

  interface Props {
    data: {
      children: {
        bind?: string[];
        dbConsoleValue: string;
        id: string;
        name: string;
      }[];
      icon: string;
      id: string;
      name: string;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const profileStore = useUserProfile();
  const { profile } = storeToRefs(profileStore);
  const eventBus = useEventBus();

  const profileFavorKey = toolboxProfileKeyMap[route.meta.dbType as DBTypes]!.favor;
  const activeViewName = ref('');

  const favorMap = computed(() => {
    return makeMap(profile.value[profileFavorKey] || []);
  });

  watch(
    route,
    () => {
      const activeItem = _.find(props.data.children, (item) =>
        Boolean(item.bind?.includes(route.name as string) || route.name === item.id),
      );
      activeViewName.value = activeItem ? activeItem.id : '';
    },
    {
      immediate: true,
    },
  );

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
    profileStore
      .updateProfile({
        label: profileFavorKey,
        values: Object.keys(lastFavorMap),
      })
      .then(() => {
        messageSuccess(successMessage);
        eventBus.emit('DB_MANAGE_TOOLBOX_FAVOR_CHANGE');
      });
  };
</script>
