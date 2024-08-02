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
  <div class="render-host-box">
    <TableSeletorInput
      ref="editRef"
      v-model="localValue"
      :rules="rules"
      @click-seletor="handleOpenSeletor" />
  </div>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type TendbhaModel from '@services/model/mysql/tendbha';
  import type TendbsingleModel from '@services/model/mysql/tendbsingle';
  import { queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  import TableSeletorInput from '@views/db-manage/common/TableSeletorInput.vue';

  interface Props {
    sourceClusterId: number;
    targetClusterId?: number;
  }

  interface Exposes {
    getValue: () => Promise<{
      target_cluster_id: number;
    }>;
  }

  type SelectedClusters = Array<TendbhaModel | TendbsingleModel>;

  const props = withDefaults(defineProps<Props>(), {
    sourceClusterId: 0,
    targetClusterId: 0,
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const isShowSelector = ref(false);

  const editRef = ref<InstanceType<typeof TableSeletorInput>>();
  const localValue = ref();
  const localClusterIds = ref<number[]>([props.targetClusterId]);
  const selectedClusters = shallowRef<{ [key: string]: SelectedClusters }>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: {
      showPreviewResultTitle: true,
      disabledRowConfig: [
        {
          handler: (data: TendbhaModel) => data.id === props.sourceClusterId,
          tip: t('不能选择源集群'),
        },
      ],
      multiple: false,
    },
    [ClusterTypes.TENDBSINGLE]: {
      showPreviewResultTitle: true,
      disabledRowConfig: [
        {
          handler: (data: TendbsingleModel) => data.id === props.sourceClusterId,
          tip: t('不能选择源集群'),
        },
      ],
      multiple: false,
    },
  } as unknown as Record<string, TabConfig>;

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => value.split(',').every((domain) => domainRegex.test(domain)),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: async (value: string) => {
        const list = value.split(batchSplitRegex);
        return await queryClusters({
          cluster_filters: list.map((item) => ({
            immute_domain: item,
          })),
          bk_biz_id: currentBizId,
        }).then((data) => {
          if (data.length === list.length) {
            return true;
          }
          return false;
        });
      },
      message: t('目标集群不存在'),
    },
  ];

  const queryClustersById = (id: number) => {
    queryClusters({
      cluster_filters: [
        {
          id,
        },
      ],
      bk_biz_id: currentBizId,
    }).then((data) => {
      if (data) {
        localValue.value = data[0].master_domain;
      }
    });
  };

  watch(
    () => props.targetClusterId,
    (id) => {
      if (id) {
        queryClustersById(id);
      }
    },
    {
      immediate: true,
    },
  );

  const handleOpenSeletor = () => {
    isShowSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: SelectedClusters }) => {
    selectedClusters.value = selected;
    const list = Object.keys(selected).reduce((list: SelectedClusters, key) => list.concat(...selected[key]), []);
    localValue.value = list.map((item) => item.master_domain).join(',');
    localClusterIds.value = list.map((item) => item.id);
    window.changeConfirm = true;
    setTimeout(() => {
      editRef.value!.getValue();
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return editRef.value!.getValue().then(() => ({
        target_cluster_id: localClusterIds.value[0],
      }));
    },
  });
</script>
<style lang="less" scoped>
  .render-host-box {
    position: relative;
  }
</style>
