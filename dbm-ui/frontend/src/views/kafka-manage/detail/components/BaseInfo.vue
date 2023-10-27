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
  <div class="cluster-detail-base-info">
    <BkLoading :loading="isLoading">
      <RenderBaseInfo :data="clusterData" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';

  import { getClusterDetail } from '@services/source/kafka';

  import { useGlobalBizs } from '@stores';

  import RenderBaseInfo from '@components/cluster-common/RenderBaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const globalBizsStore = useGlobalBizs();

  const isLoading = ref(true);
  const clusterData = ref<any>({});

  const fetchData = () => {
    isLoading.value = true;
    getClusterDetail({
      bk_biz_id: globalBizsStore.currentBizId,
      cluster_id: props.clusterId,
    })
      .then((data) => {
        clusterData.value = data;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };
  watch(() => props.clusterId, () => {
    fetchData();
  }, {
    immediate: true,
  });
</script>

<style lang="less" scoped>
.cluster-detail-base-info {
  width: 100%;
}
</style>
