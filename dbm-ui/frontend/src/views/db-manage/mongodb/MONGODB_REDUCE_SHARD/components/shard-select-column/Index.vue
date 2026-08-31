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
  <EditableColumn
    :disabled-method="() => (!clusterId ? t('请先选择集群') : false)"
    field="shard_names"
    :label="t('缩容分片')"
    :loading="isLoading"
    :min-width="250"
    required
    :width="250">
    <EditableSelect
      v-model="modelValue"
      :list="shardSelectList"
      multiple />
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listClusterShards } from '@services/source/mongodbToolbox';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const shardOptions = ref<string[]>([]);

  const shardSelectList = computed(() => shardOptions.value.map((name) => ({ label: name, value: name })));

  const { loading: isLoading, run: fetchShards } = useRequest(listClusterShards, {
    manual: true,
    onSuccess(data) {
      const clusterShards = data.find((item) => item.cluster_id === props.clusterId);
      shardOptions.value = clusterShards?.shard_list || [];
      // 过滤掉不属于新集群的已选分片（框架层对引用类型做了实际值变化才校验的守卫）
      modelValue.value = modelValue.value.filter((name) => shardOptions.value.includes(name));
    },
  });

  // 集群变化时重新加载分片选项；不主动清空已选（回显场景集群解析后 clusterId 才变化，清空会丢掉回填数据），
  // 不属于该集群的已选分片在选项加载后由 onSuccess 过滤
  watch(
    () => props.clusterId,
    (clusterId) => {
      shardOptions.value = [];
      if (clusterId) {
        fetchShards({
          cluster_ids: [clusterId],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
