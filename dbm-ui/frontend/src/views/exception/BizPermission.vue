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
  <BkException
    style="margin-top: 150px;"
    :title="$t('无业务权限')"
    type="403">
    <p class="mb-24">
      {{ $t('你没有相应业务的访问权限_请前往申请相关业务权限或创建业务') }}
    </p>
    <BkButton
      class="mr-8"
      :loading="isLoading"
      theme="primary"
      @click="fetchResourcePermission">
      {{ $t('申请业务权限') }}
    </BkButton>
    <BkButton
      theme="primary"
      @click="handleToCreate">
      {{ $t('创建业务') }}
    </BkButton>
  </BkException>
</template>

<script setup lang="ts">
  import { getApplyDataLink } from '@services/source/iam';

  import { useSystemEnviron } from '@stores';

  const systemEnvironStore = useSystemEnviron();

  const isLoading = ref(false);

  const handleToCreate = () => {
    const { BK_CMDB_URL } = systemEnvironStore.urls;
    if (BK_CMDB_URL) {
      window.open(`${BK_CMDB_URL}/#/resource/business`, '_blank');
    }
  };

  /**
   * 获取鉴权资源信息
   */
  const fetchResourcePermission = () => {
    isLoading.value = true;
    getApplyDataLink({
      action_ids: ['DB_MANAGE'],
      resources: [],
    })
      .then((res) => {
        window.open(res.apply_url, '__blank');
      })
      .finally(() => {
        isLoading.value = false;
      });
  };
</script>
