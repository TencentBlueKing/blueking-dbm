<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkResizeLayout
    :border="false"
    class="db-manage-toolbox"
    collapsible
    disabled
    initial-divide="300px">
    <template #aside>
      <ToolNavigation
        :data="menuList"
        :menu-group-list="menuGroupList" />
    </template>
    <template #main>
      <div class="db-manage-toolbox-page">
        <div class="toolbox-page-title">
          <span style="font-weight: bold">{{ toolName }}</span>
          <BkTag
            class="ml-8"
            theme="info">
            {{ dbType }}
          </BkTag>
        </div>
        <div
          ref="contentWrapper"
          class="toolbox-page-content">
          <ScrollFaker style="padding: 0 24px">
            <RouterView :key="route.path" />
          </ScrollFaker>
        </div>
        <Teleport
          v-if="teleportTarget && submitErrorMessage && submitErrorMessage.length > 0"
          :to="teleportTarget">
          <BkAlert
            class="mt-20 mb-20"
            theme="danger">
            <template #title>
              {{ submitErrorMessage }}
            </template>
          </BkAlert>
        </Teleport>
      </div>
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { watch } from 'vue';
  import { useRoute } from 'vue-router';

  import { useEventBus } from '@hooks';

  import ToolNavigation, { type Props as ToolNavigationProps } from './components/tool-navigation/Index.vue';

  interface Props {
    menuGroupList?: ToolNavigationProps['menuGroupList'];
    menuList: ToolNavigationProps['data'];
  }

  defineProps<Props>();

  const route = useRoute();
  const eventBus = useEventBus();

  const contentWrapperRef = useTemplateRef('contentWrapper');
  const toolName = ref('');
  const dbType = ref('');
  const teleportTarget = shallowRef<HTMLDivElement>();
  const submitErrorMessage = ref<string>('');

  watch(
    route,
    () => {
      toolName.value = route.meta.navName as string;
      dbType.value = _.upperFirst(route.meta.dbType as string);
      submitErrorMessage.value = '';
    },
    {
      immediate: true,
    },
  );

  eventBus.on('db-toolbox-error', (errorMessage: any) => {
    submitErrorMessage.value = errorMessage;
    nextTick(() => {
      teleportTarget.value?.scrollIntoView({
        behavior: 'smooth',
      });
    });
  });

  eventBus.on('editable-table-model-change', () => {
    submitErrorMessage.value = '';
  });

  onMounted(() => {
    teleportTarget.value = contentWrapperRef.value?.querySelector('.smart-action-bottom-placeholder') as HTMLDivElement;
  });
</script>
<style lang="less">
  .db-manage-toolbox {
    height: calc(100vh - var(--notice-height) - 105px);

    & > .bk-resize-layout-aside {
      z-index: 100;

      &::after {
        display: none;
      }
    }

    .db-manage-toolbox-page {
      height: 100%;
      background-color: white;

      .toolbox-page-title {
        display: flex;
        width: 100%;
        height: 54px;
        padding: 0 24px;
        align-items: center;
        font-size: 14px;
        color: #313238;
      }

      .toolbox-page-content {
        height: calc(100% - 52px);
      }

      .toolbox-error-message {
        background-color: #f5f7fa;
      }
    }
  }
</style>
