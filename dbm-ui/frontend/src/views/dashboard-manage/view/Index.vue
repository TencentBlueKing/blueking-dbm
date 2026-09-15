<template>
  <div
    ref="root"
    style="margin: 0 -10px" />
  <Teleport
    v-if="currentViewName"
    to="#dbContentTitleAppend">
    {{ currentViewName }}
  </Teleport>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import urlJoin from 'url-join';
  import { useTemplateRef } from 'vue';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getAppShareList } from '@services/source/bkVersion';

  const route = useRoute();

  const { data: appShareList } = useRequest(getAppShareList);
  const rootRef = useTemplateRef('root');

  const versionId = ref((route.params.versionId as string) || '');
  const currentViewName = computed(() => {
    if (!appShareList.value) {
      return '';
    }

    return _.find(appShareList.value, (item) => item.uid === versionId.value)?.name;
  });

  let app: ServiceReturnType<typeof window.BkVisionSDK.init>;
  watch(
    route,
    () => {
      if (app) {
        app.unmount();
      }
      versionId.value = route.params.versionId as string;
      nextTick(async () => {
        app = await window.BkVisionSDK.init(rootRef.value!, versionId.value, {
          apiPrefix: urlJoin(window.BK_AJAX_URL, `/bkvision/`),
          chartToolMenu: [
            {
              build_in: true,
              id: 'fullscreen',
              type: 'tool',
            }, // 全屏
            {
              build_in: true,
              id: 'refresh',
              type: 'tool',
            }, // 刷新
            {
              build_in: true,
              id: 'excel',
              type: 'menu',
            }, // 导出
          ],
          toolMenu: [
            {
              build_in: true,
              id: 'screenshot',
            },
          ],
          waterMark: {
            content: 'bk-vision',
          },
        });
      });
    },
    {
      immediate: true,
    },
  );
</script>
