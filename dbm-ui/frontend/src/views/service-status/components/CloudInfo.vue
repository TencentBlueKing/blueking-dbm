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
  <div
    v-bk-loading="{ loading: fetchCloudLoading }"
    class="service-status-cloud-info">
    <div class="ml-12 mr-12 mb-12">
      <BkInput
        v-model.tirm="serachKey"
        clearable
        :placeholder="t('请输入')"
        type="search" />
    </div>
    <EmptyStatus
      v-if="cloudList.length === 0"
      :is-anomalies="!!fetchClondError"
      is-searching
      @clear-search="handleClearSearch"
      @refresh="runFetchAvailableClouds" />
    <div
      v-else
      class="cloud-info-list">
      <ScrollFaker>
        <div
          v-for="item in cloudList"
          :key="item.bk_cloud_id"
          class="service-status-cloud-item"
          :class="{ 'service-status-cloud-item-current': modelValue === item.bk_cloud_id }"
          @click="handleClick(item.bk_cloud_id)">
          <span class="cloud-name">{{ item.bk_cloud_name }}</span>
          <span class="cloud-id ml-4">[{{ item.bk_cloud_id }}]</span>
        </div>
      </ScrollFaker>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { fetchAvailableClouds } from '@services/source/dbextension';

  import { useDebouncedRef } from '@hooks';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  const modelValue = defineModel<number>({ required: true });

  const { t } = useI18n();

  const serachKey = useDebouncedRef('');

  const cloudList = computed(() => {
    if (serachKey.value === '') {
      return availableClouds.value || [];
    }
    return _.filter(availableClouds.value, (cloudItem) => cloudItem.bk_cloud_name.includes(serachKey.value));
  });

  const {
    data: availableClouds,
    error: fetchClondError,
    loading: fetchCloudLoading,
    run: runFetchAvailableClouds,
  } = useRequest(fetchAvailableClouds, {
    manual: true,
  });

  watch(serachKey, () => {
    modelValue.value = -1;
  });

  watch(cloudList, () => {
    if (cloudList.value.length > 0) {
      modelValue.value = cloudList.value[0].bk_cloud_id;
    }
  });

  const handleClearSearch = () => {
    serachKey.value = '';
  };

  const handleClick = (id: number) => {
    if (id === modelValue.value) {
      return;
    }
    modelValue.value = id;
  };

  onMounted(() => {
    runFetchAvailableClouds();
  });
</script>

<style lang="less">
  .service-status-cloud-info {
    width: 260px;
    height: 100%;
    padding: 16px 0;
    background-color: #fff;
    flex-shrink: 0;

    .cloud-info-list {
      height: calc(100% - 48px);

      .service-status-cloud-item {
        display: flex;
        height: 40px;
        padding: 0 24px;
        cursor: pointer;
        align-items: center;

        .cloud-name {
          color: #4d4f56;
        }

        .cloud-id {
          font-size: 12px;
          color: #979ba5;
        }

        &:hover {
          background-color: #f5f7fa;
        }
      }

      .service-status-cloud-item-current {
        background-color: #e1ecff;
        border-right: 2px solid #3a84ff;

        .cloud-name {
          color: #3a84ff;
        }

        &:hover {
          background-color: #e1ecff;
        }
      }
    }
  }
</style>
