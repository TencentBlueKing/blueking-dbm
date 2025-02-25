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
    class="dba-manage-mysql-page"
    collapsible
    disabled
    initial-divide="300px">
    <template #aside>
      <div class="dba-manage-mysql-side">
        <BkInput
          v-model.tirm="serachKey"
          class="toolbox-side-search mt-16 mb-12"
          clearable
          :placeholder="t('请输入')"
          type="search" />
        <div class="toolbox-side-collapse">
          <ScrollFaker>
            <div
              v-for="item in routes"
              :key="item.id"
              class="menu-item"
              :class="{ 'menu-item-active': item.id === activeMenu }"
              @click="() => handleMenuClick(item.id)">
              {{ item.name }}
            </div>
          </ScrollFaker>
        </div>
      </div>
    </template>
    <template #main>
      <div class="toolbox-page-wrapper">
        <div class="toolbox-page-title">
          <span style="font-weight: bold">{{ toolboxTitle }}</span>
          <BkTag
            class="ml-8"
            theme="info">
            MySQL
          </BkTag>
        </div>
        <div
          :key="route.path"
          class="toolbox-content-wrapper">
          <ScrollFaker style="padding: 0 24px">
            <RouterView />
          </ScrollFaker>
        </div>
      </div>
    </template>
  </BkResizeLayout>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import { useDebouncedRef } from '@hooks';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const serachKey = useDebouncedRef('');

  const toolboxTitle = ref('');
  const activeMenu = ref('DbaManageMysqlWebQuery');

  const routes = [
    {
      dbConsoleValue: '',
      id: 'DbaManageMysqlWebQuery',
      name: t('Web 查询'),
    },
  ];

  watch(
    route,
    () => {
      toolboxTitle.value = route.meta.navName as string;
    },
    {
      immediate: true,
    },
  );

  watch(
    activeMenu,
    () => {
      router.push({ name: activeMenu.value });
    },
    {
      immediate: true,
    },
  );

  const handleMenuClick = (id: string) => {
    activeMenu.value = id;
  };
</script>
<style lang="less">
  .dba-manage-mysql-page {
    height: calc(100vh - 105px);

    & > .bk-resize-layout-aside {
      z-index: 100;

      &::after {
        display: none;
      }
    }

    .dba-manage-mysql-side {
      height: 100%;
      background-color: #f5f7fa;

      .toolbox-side-search {
        display: flex;
        width: calc(100% - 32px);
        margin: 0 auto;
      }

      .toolbox-side-collapse {
        height: calc(100% - 40px);
        margin-top: 8px;

        .menu-item {
          display: flex;
          height: 32px;
          padding-left: 16px;
          margin: 0 16px;
          margin-bottom: 8px;
          font-size: 12px;
          cursor: pointer;
          background: #fff;
          border-radius: 2px;
          align-items: center;

          &.menu-item-active {
            color: #3a84ff;
            background: #e1ecff;
          }
        }
      }
    }

    .toolbox-page-wrapper {
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

      .toolbox-content-wrapper {
        height: calc(100% - 52px);
      }
    }
  }
</style>
