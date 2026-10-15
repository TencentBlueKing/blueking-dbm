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
    <DbSelect
      v-model="modelValue"
      class="item-input"
      :clearable="false"
      :disabled="isAdjustApply"
      filterable
      :input-search="false"
      :loading="isLoading">
      <DbOption
        v-for="item in bcsClusterList"
        :key="item.clusterName"
        :label="item.clusterName"
        :value="item.clusterName" />
    </DbSelect>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getBcsClusters } from '@services/source/kubernetesToolbox';

  import { useTicketModifyState } from '@hooks';

  interface Props {
    applyMode?: string;
    bkBizId?: number | string;
    regionCode: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    applyMode: 'SharedMode',
    bkBizId: '',
  });
  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();
  // 调整申请模式只放开资源申请条件，本项只读
  const isAdjustApply = Boolean(useTicketModifyState()?.isAdjustApply);

  // 独占集群（isPublic=false）时按业务 ID 取该业务独占的 BCS 集群资源
  const isPublic = computed(() => props.applyMode !== 'ExclusiveMode');
  const bkBizId = computed(() => (props.bkBizId ? Number(props.bkBizId) : undefined));

  const bcsClusterList = computed(() => {
    return (bcsClusterData?.value || []).find((item) => item.regionCode === props.regionCode)?.k8sClusterList || [];
  });

  // 当前列表对应的部署类型；切换部署类型后新列表返回前，旧列表不能用来判断已选集群是否失效
  let loadedIsPublic: boolean | undefined;

  const {
    data: bcsClusterData,
    loading: isLoading,
    run,
  } = useRequest(getBcsClusters, {
    manual: true,
    onSuccess(_data, [params]) {
      loadedIsPublic = params.isPublic;
    },
  });

  watch(
    [isPublic, bkBizId],
    () => {
      // 业务 ID 未就绪时不请求，避免回显过程中先按默认业务取一次造成结果竞态
      if (!bkBizId.value) {
        return;
      }
      run({
        bkBizId: bkBizId.value,
        isPublic: isPublic.value,
      });
    },
    { immediate: true },
  );

  // 部署类型/地域变化后已选集群可能不在新列表中，清空避免提交失效数据
  watch(bcsClusterList, (list) => {
    // 列表未返回时不清空：回填会先把值写入，regionCode 变化会让空列表抢先触发误判；
    // 列表还是另一种部署类型的（如改单「重置」同时改回部署类型与地域）也不清空，等新列表返回再判断
    if (!bcsClusterData.value || loadedIsPublic !== isPublic.value) {
      return;
    }
    if (modelValue.value && !list.some((item) => item.clusterName === modelValue.value)) {
      modelValue.value = '';
    }
  });
</script>
