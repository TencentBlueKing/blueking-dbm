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
  <div>
    <BkRadioGroup
      v-model="activeTab"
      type="capsule"
      @change="handleChange">
      <BkRadioButton label="operation-view">
        <DbIcon
          class="mr-4"
          type="bk-dbm-icon db-icon-legend" />
        {{ t('补货操作视角') }}
      </BkRadioButton>
      <BkRadioButton label="ticket-view">
        <DbIcon
          class="mr-4"
          type="bk-dbm-icon db-icon-danju" />
        {{ t('补货单据视角') }}
      </BkRadioButton>
    </BkRadioGroup>
    <BkButton
      class="ml-12 forward-btn"
      text
      theme="primary"
      @click="handleForward">
      {{ t('跳转待补货列表') }}
      <DbIcon
        class="ml-6"
        type="bk-dbm-icon db-icon-link" />
    </BkButton>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const activeTab = ref((route.params.page as string) || 'operation-view');

  const handleForward = () => {
    router.push({
      name: 'resourcePool',
      params: {
        page: 'replenish-list',
      },
    });
  };

  const handleChange = (value: string) => {
    router.push({
      name: 'resourceReplenishRecord',
      params: {
        page: value,
      },
    });
  };
</script>
