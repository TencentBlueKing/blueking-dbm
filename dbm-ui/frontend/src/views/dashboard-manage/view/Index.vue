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

  let app: ServiceReturnType<typeof window.BkVisionSDK.init> | undefined;
  // 多次切换仪表盘时串行初始化：等上一次 init 完成并卸载后再挂新的，避免先发后到的旧仪表盘挂到同一节点
  let initTask = Promise.resolve();
  watch(
    route,
    () => {
      versionId.value = route.params.versionId as string;
      const currentVersionId = versionId.value;
      initTask = initTask
        .then(async () => {
          // 排队期间又切走了，跳过这次
          if (currentVersionId !== versionId.value) {
            return;
          }
          if (app) {
            app.unmount();
            // 卸载后立即清空：本次 init 失败时，下次切换不会再卸载同一个旧实例
            app = undefined;
          }
          await nextTick();
          app = await window.BkVisionSDK.init(rootRef.value!, currentVersionId, {
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
        })
        .catch(() => {
          // 单次初始化失败不能卡住后续切换
        });
    },
    {
      immediate: true,
    },
  );
</script>
