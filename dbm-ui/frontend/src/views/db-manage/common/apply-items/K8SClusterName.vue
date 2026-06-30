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
  <BkFormItem
    :label="t('BCS 集群')"
    property="details.k8s_cluster_name"
    required>
    <BkSelect
      v-model="modelValue"
      class="item-input"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="isLoading">
      <BkOption
        v-for="item in bcsClusterList"
        :key="item.clusterName"
        :label="item.clusterName"
        :value="item.clusterName" />
    </BkSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBcsClusters } from '@services/source/kubernetesToolbox';

  interface Props {
    regionCode: string;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const bcsClusterList = computed(() => {
    return (bcsClusterData?.value || []).find((item) => item.regionCode === props.regionCode)?.k8sClusterList || [];
  });

  const { data: bcsClusterData, loading: isLoading } = useRequest(getBcsClusters, {
    defaultParams: [
      {
        isPublic: true,
      },
    ],
  });
</script>
