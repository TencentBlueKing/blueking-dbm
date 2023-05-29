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
  <BkLoading :loading="isLoading">
    <div class="render-cluster-box">
      <div>
        <div
          v-for="item in relatedClusterList"
          :key="item.id"
          class="relate-cluster-list">
          {{ item.master_domain }}
        </div>
        <span
          v-if="relatedClusterList.length < 1"
          key="empty"
          style="color: #c4c6cc;">
          {{ $t('输入主库后自动生成') }}
        </span>
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import {
    ref,
    shallowRef,
    watch,
  } from 'vue';

  import { checkInstances  } from '@services/clusters';
  import type { InstanceInfos } from '@services/types/clusters';

  import { useGlobalBizs } from '@stores';

  import type { IHostData } from './Row.vue';

  interface Props {
    masterData?: IHostData
  }

  interface Emits {
    (e: 'change', value: number[]): void
  }
  interface Exposes {
    getValue: () => Promise<Record<'cluster_ids', number[]>>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();

  const isLoading = ref(false);
  const relatedClusterList = shallowRef<InstanceInfos['related_clusters']>([]);

  watch(() => props.masterData, () => {
    relatedClusterList.value = [];
    emits('change', []);
    if (props.masterData && props.masterData.ip) {
      isLoading.value = true;
      checkInstances(currentBizId, {
        instance_addresses: [props.masterData.ip],
      }).then((data) => {
        if (data.length < 1) {
          return;
        }

        const [currentProxyData] = data;
        relatedClusterList.value = currentProxyData.related_clusters;
        emits('change', relatedClusterList.value.map(item => item.id));
      })
        .finally(() => {
          isLoading.value = false;
        });
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return Promise.resolve({
        cluster_ids: relatedClusterList.value.map(item => item.id),
      });
    },
  });
</script>
<style lang="less" scoped>
  .render-cluster-box {
    padding: 10px 16px;
    line-height: 20px;
  }
</style>
