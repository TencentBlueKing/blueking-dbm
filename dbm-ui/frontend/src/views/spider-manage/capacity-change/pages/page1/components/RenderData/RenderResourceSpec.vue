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
    <TableEditInput
      ref="inputRef"
      :model-value="`${localClusterData ? localClusterData.cluster_spec.spec_name : ''}`"
      :placeholder="$t('输入集群后自动生成')"
      readonly
      textarea />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import type SpiderModel from '@services/model/spider/spider';
  import { getDetail } from '@services/spider';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  interface Props {
    clusterId: number,
  }
  interface Emits {
    (e: 'cluster-change', value: SpiderModel): void
  }
  interface Exposes {
    getValue: () => Promise<{
      bk_cloud_id: number,
      cluster_shard_num: number,
      db_module_id: number
    }>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const inputRef = ref();
  const masterInstance = ref('');
  const localClusterData = ref<SpiderModel>();

  const {
    loading: isLoading,
    run: fetchClusetrData,
  } = useRequest(getDetail, {
    manual: true,
    onSuccess(data) {
      [masterInstance.value] = data.spider_master[0].instance;
      localClusterData.value = data;
      emits('cluster-change', data);
    },
  });

  watch(() => props.clusterId, () => {
    if (props.clusterId) {
      fetchClusetrData({
        id: props.clusterId,
      });
    } else {
      localClusterData.value = undefined;
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return inputRef.value
        .getValue()
        .then(() => {
          if (!localClusterData.value) {
            return Promise.reject();
          }
          const clusterData = localClusterData.value;
          return ({
            bk_cloud_id: clusterData.bk_cloud_id,
            cluster_shard_num: clusterData.cluster_shard_num,
            db_module_id: clusterData.db_module_id,
            remote_shard_num: Math.ceil(clusterData.cluster_shard_num / clusterData.machine_pair_cnt),
          });
        });
    },
  });
</script>
