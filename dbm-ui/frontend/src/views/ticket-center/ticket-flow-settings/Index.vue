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
  <Teleport to="#dbContentTitleAppend">
    <BkTag
      class="ml-8"
      theme="info">
      {{ t('业务') }}
    </BkTag>
  </Teleport>
  <div class="ticket-flow-settings">
    <div class="tab-header">
      <DbTabForBiz
        v-model="activeTab"
        ignore-cluster-count />
    </div>
    <div class="list-wrapper">
      <List :db-type="activeTab" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import { DBTypes } from '@common/const';

  import DbTabForBiz from '@components/db-tab-for-biz/Index.vue';

  import List from './components/List.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const activeTab = ref<DBTypes>((route.params.dbType as DBTypes) || DBTypes.MYSQL);

  watch(
    activeTab,
    (value) => {
      if (value) {
        router.replace({
          name: 'TicketFlowSetting',
          params: {
            dbType: value,
          },
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  .ticket-flow-settings {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;

    .tab-header {
      position: sticky;
      top: 0;
      z-index: 10;
      flex-shrink: 0;
      background: #fff;
    }

    .list-wrapper {
      flex: 1;
      min-height: 0;
      overflow: hidden;
    }
  }
</style>
