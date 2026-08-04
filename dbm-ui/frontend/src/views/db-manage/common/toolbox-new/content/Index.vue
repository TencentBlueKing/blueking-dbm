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
  <div class="db-manage-toolbox-page">
    <div
      ref="contentWrapper"
      class="toolbox-page-content"
      :class="{ 'toolbox-page-content-padding': selectedValue }">
      <ScrollFaker style="height: 100%">
        <div
          v-if="selectedValue"
          class="content-head">
          <span class="content-head-title">{{ navName }}</span>
          <BkTag
            v-if="isFix"
            class="ml-4"
            size="small"
            theme="warning">
            {{ t('故障修复') }}
          </BkTag>
        </div>
        <RouterView :key="renderKey" />
      </ScrollFaker>
    </div>
    <Teleport to="#dbContentTitleAppend">
      <div class="toolbox-page-header">
        <span class="header-title">{{ DBTypeInfos[dbType as DBTypes].name }} {{ t('工具箱') }}</span>
        <template v-if="selectedValue">
          <span class="title-divider">|</span>
          <BkSelect
            v-model="selectedValue"
            filterable
            @change="handleChange">
            <template #trigger>
              <div class="title-trigger">
                <span class="mr-8">{{ toolName }}</span>
                <DbIcon type="down-shape" />
              </div>
            </template>
            <BkOptionGroup
              v-for="item in dataList"
              :key="item.id"
              collapsible
              :label="item.name">
              <BkOption
                v-for="childItem in item.children"
                :id="childItem.id"
                :key="childItem.id"
                :name="childItem.name"
                style="justify-content: space-between">
                <div>{{ childItem.name }}</div>
                <BkTag
                  v-if="childItem.isFix"
                  size="small"
                  theme="warning">
                  {{ t('故障修复') }}
                </BkTag>
              </BkOption>
            </BkOptionGroup>
          </BkSelect>
        </template>
      </div>
    </Teleport>
    <Teleport
      v-if="teleportTarget"
      :to="teleportTarget">
      <BkAlert
        v-if="submitErrorMessage"
        class="mt-20 mb-20"
        theme="danger">
        <template #title>
          <div style="line-height: 20px; white-space: pre-line">{{ submitErrorMessage }}</div>
        </template>
      </BkAlert>
    </Teleport>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { storeToRefs } from 'pinia';
  import { watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { useEventBus } from '@hooks';

  import { useUserProfile } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import { random } from '@utils';

  import type { ToolboxLeafNode, ToolboxTreeNode } from '../common/types';
  import { isLeafNode, isTreeNode } from '../common/utils';

  interface Props {
    menuList: ToolboxTreeNode[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const eventBus = useEventBus();
  const profileStore = useUserProfile();
  const { profile } = storeToRefs(profileStore);

  const dataList = props.menuList.map((item) => {
    const firstChild = item.children[0];
    if (firstChild && isTreeNode(firstChild)) {
      const list = item.children
        .filter((child): child is ToolboxTreeNode => isTreeNode(child))
        .flatMap((childItem) =>
          childItem.children.filter((subChild): subChild is ToolboxLeafNode => isLeafNode(subChild)),
        );
      return {
        ...item,
        children: list,
      };
    }
    return {
      ...item,
      children: item.children.filter((child): child is ToolboxLeafNode => isLeafNode(child)),
    };
  });

  const profileUsedKey = `${route.meta.dbType}_toolbox_used`.toUpperCase();

  const contentWrapperRef = useTemplateRef('contentWrapper');
  const dbType = ref('');
  const teleportTarget = shallowRef<HTMLDivElement>();
  const submitErrorMessage = ref<string>('');
  const renderKey = ref(random());
  const toolName = ref('');
  const selectedValue = ref('');

  const navName = computed(() => route.meta.navName);
  const isFix = computed(() => {
    const selectId = selectedValue.value;
    return dataList.flatMap((item) => item.children).find((item: ToolboxLeafNode) => item.id === selectId)?.isFix;
  });

  const MAX_USED_COUNT = 6;
  const handleRouterUsed = (routerId: string) => {
    let lastUsed = [routerId].concat((profile.value[profileUsedKey] || []).filter((item: string) => item !== routerId));
    if (lastUsed.length > MAX_USED_COUNT) {
      lastUsed = lastUsed.slice(0, MAX_USED_COUNT);
    }
    profileStore.updateProfile({
      label: profileUsedKey,
      values: lastUsed,
    });
  };

  watch(
    route,
    () => {
      const allLeafItems = dataList.flatMap((item) => item.children) as ToolboxLeafNode[];
      const activeItem = _.find(allLeafItems, (item: ToolboxLeafNode) =>
        Boolean(item.bind?.includes(route.name as string) || route.name === item.id),
      );
      toolName.value = activeItem ? activeItem.name : '';
      if (activeItem?.id) {
        selectedValue.value = activeItem.id;
        handleRouterUsed(activeItem.id);
      } else {
        selectedValue.value = '';
      }
      dbType.value = route.meta.dbType as string;
      submitErrorMessage.value = '';
      nextTick(() => {
        teleportTarget.value = contentWrapperRef.value?.querySelector(
          '.smart-action-bottom-placeholder',
        ) as HTMLDivElement;
      });
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: string) => {
    router.push({
      name: value,
    });
  };

  // 提单成功，刷新页面
  eventBus.on('db-toolbox-success', () => {
    router.replace({
      path: route.path,
      query: {},
    });
    setTimeout(() => {
      renderKey.value = random();
    }, 60);
  });

  // 提单失败，展示错误信息
  eventBus.on('db-toolbox-error', (errorMessage: string) => {
    submitErrorMessage.value = errorMessage;
    nextTick(() => {
      teleportTarget.value?.scrollIntoView({
        behavior: 'smooth',
      });
    });
  });

  // 工具箱编辑表格数据变化
  eventBus.on('editable-table-model-change', () => {
    submitErrorMessage.value = '';
  });
</script>
<style lang="less">
  .toolbox-page-header {
    display: flex;
    align-items: center;

    .header-title {
      font-size: 16px;
      color: #313238;
    }

    .title-divider {
      margin-right: 6px;
      margin-left: 6px;
      color: #dcdee5;
    }

    .title-trigger {
      width: 240px;
      font-size: 14px;
      color: #3a84ff;
      cursor: pointer;
    }
  }

  .db-manage-toolbox-page {
    height: 100%;
    padding: 24px;

    .toolbox-page-content {
      height: 100%;
      background-color: #fff;
      // height: calc(100% - 52px);

      &.toolbox-page-content-padding {
        padding: 16px 24px;
      }

      .content-head {
        display: flex;
        align-items: center;
        padding-bottom: 12px;
        margin-bottom: 16px;
        border-bottom: 1px solid #eaebf0;

        .content-head-title {
          font-size: 14px;
          font-weight: bolder;
          color: #313238;
        }
      }
    }

    .toolbox-error-message {
      background-color: #f5f7fa;
    }
  }
</style>
