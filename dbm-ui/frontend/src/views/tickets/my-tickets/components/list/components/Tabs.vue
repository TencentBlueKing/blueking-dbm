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
  <BkTab
    v-if="userProfile.isManager"
    v-model:active="curTab"
    class="ticket-tabs"
    type="card-tab"
    @change="handleChangeTab">
    <BkTabPanel
      :label="$t('我申请的')"
      name="personal" />
    <BkTabPanel
      :label="$t('与我相关的')"
      name="all" />
  </BkTab>
</template>

<script setup lang="ts">
  import { useUserProfile } from '@stores';

  interface Emits {
    (e: 'change', value: string): void,
  }

  const emits = defineEmits<Emits>();

  const route = useRoute();
  const router = useRouter();
  const userProfile = useUserProfile();

  const curTab = ref('personal');

  const changeRoute = () => {
    let typeId = route.params.typeId as string ?? 'personal';

    if (route.query.filterId && userProfile.isManager) {
      typeId = 'all';
    } else if (typeId === 'all' && !userProfile.isManager) {
      typeId = 'personal';
    }
    router.replace({
      params: {
        typeId,
      },
      query: { ...(route.query || {}) },
    });
    curTab.value = typeId;
    emits('change', typeId);
  };

  onBeforeMount(() => {
    changeRoute();
  });

  const handleChangeTab = (typeId: string) => {
    console.log('handleChangeTab');
    router.replace({
      params: {
        typeId,
      },
      query: { ...(route.query || {}) },
    });
    emits('change', typeId);
  };
</script>

<style lang="less" scoped>
  .ticket-tabs {
    margin-bottom: 12px;

    :deep(.bk-tab-header) {
      width: 100%;
      height: 32px;
      font-size: 12px;
      line-height: 32px !important;
      border-radius: 2px;

      .bk-tab-header-nav {
        width: 100%;
        align-items: center;
      }

      .bk-tab-header-item {
        height: 24px;
        margin: 0 4px;
        line-height: 24px !important;
        border-radius: 2px;
        flex: 1;

        &:last-child::after {
          display: none;
        }

        &:not(:first-of-type)::before {
          left: -4px;
          display: block !important;
        }
      }
    }

    :deep(.bk-tab-content) {
      display: none;
    }
  }
</style>
