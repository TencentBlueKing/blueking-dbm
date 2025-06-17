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
  <div class="service-status-service-info">
    <ScrollFaker v-bk-loading="{ loading: fetchExtensionLoading }">
      <template v-if="extensionData">
        <ItemContainer
          :data="extensionData['NGINX']"
          title="NGINX">
          <NginxTable :list="extensionData['NGINX']" />
        </ItemContainer>
        <ItemContainer
          class="mt-16"
          :data="extensionData['DNS']"
          title="DNS">
          <DnsTable :list="extensionData['DNS']" />
        </ItemContainer>
        <ItemContainer
          class="mt-16"
          :data="extensionData['DRS']"
          title="DRS">
          <DrsTable :list="extensionData['DRS']" />
        </ItemContainer>
        <ItemContainer
          class="mt-16"
          :data="extensionData['REDIS_DTS']"
          title="REDIS_DTS">
          <RedisDtsTable :list="extensionData['REDIS_DTS']" />
        </ItemContainer>
        <ItemContainer
          class="mt-16"
          :data="extensionData['DBHA']"
          title="DBHA">
          <DbhaTable :list="extensionData['DBHA']" />
        </ItemContainer>
      </template>
      <EmptyStatus
        v-else
        :is-anomalies="!!fetchExtensionError"
        :is-searching="false"
        @refresh="fetchData" />
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { fetchExtensions } from '@services/source/dbextension';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import ItemContainer from './components/ItemContainer.vue';
  import DbhaTable from './components/table/DbhaTable.vue';
  import DnsTable from './components/table/DnsTable.vue';
  import DrsTable from './components/table/DrsTable.vue';
  import NginxTable from './components/table/NginxTable.vue';
  import RedisDtsTable from './components/table/RedisDtsTable.vue';

  const modelValue = defineModel<number>({ required: true });

  const {
    data: extensionData,
    error: fetchExtensionError,
    loading: fetchExtensionLoading,
    run: runFetchExtensions,
  } = useRequest(fetchExtensions, {
    debounceInterval: 200,
    manual: true,
  });

  watch(modelValue, () => {
    if (modelValue.value === -1) {
      extensionData.value = undefined;
    } else {
      fetchData();
    }
  });

  const fetchData = () => {
    runFetchExtensions({
      bk_cloud_id: modelValue.value,
    });
  };
</script>

<style lang="less">
  .service-status-service-info {
    width: calc(100% - 260px);
    height: 100%;
    padding: 24px;
  }
</style>
