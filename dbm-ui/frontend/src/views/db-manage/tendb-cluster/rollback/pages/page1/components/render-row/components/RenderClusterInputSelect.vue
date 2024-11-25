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
      v-model="localClusterDomain"
      :rules="rules"
      @click-seletor="handleOpenSeletor" />
  </div>
  <ClusterSelector
    v-model:is-show="isShowSelector"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handelClusterChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { queryClusters } from '@services/source/mysqlCluster';
  import { getTendbClusterList } from '@services/source/tendbcluster';

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

  const props = withDefaults(defineProps<Props>(), {
    sourceClusterId: 0,
    targetClusterId: 0,
  });

  const { t } = useI18n();

  const editRef = ref<InstanceType<typeof TableSeletorInput>>();
  const isShowSelector = ref(false);
  const localClusterDomain = ref('');
  const localClusterId = ref<number>(props.targetClusterId);
  const selectedClusters = shallowRef<{ [key: string]: Array<TendbClusterModel> }>({
    [ClusterTypes.TENDBCLUSTER]: [],
  });

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: {
      disabledRowConfig: [
        {
          handler: (data: TendbhaModel) => data.id === props.sourceClusterId,
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
      validator: (value: string) => domainRegex.test(value),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: async (value: string) => {
        const list = value.split(batchSplitRegex);
        return await queryClusters({
          cluster_filters: list.map((item) => ({
            immute_domain: item,
          })),
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        }).then((data) => {
          if (data.length === list.length) {
            localClusterId.value = data[0].id;
            return true;
          }
          return false;
        });
      },
      message: t('目标集群不存在'),
    },
  ];

  const queryClustersById = (id: number) => {
    getTendbClusterList({
      cluster_ids: [id],
    }).then((data) => {
      if (data?.results.length > 0) {
        localClusterId.value = data.results[0]?.id;
        localClusterDomain.value = data.results[0]?.master_domain;
      }
    });
  };

  const handleOpenSeletor = () => {
    isShowSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: TendbClusterModel[] }) => {
    selectedClusters.value = selected;
    const list = Object.values(selected).flat();
    const [firstItem] = list;
    localClusterDomain.value = firstItem.master_domain;
    localClusterId.value = firstItem.id;
    window.changeConfirm = true;
    setTimeout(() => {
      editRef.value!.getValue();
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

  defineExpose<Exposes>({
    getValue() {
      return editRef.value!.getValue().then(() => ({
        target_cluster_id: localClusterId.value,
      }));
    },
  });
</script>
<style lang="less" scoped>
  .render-host-box {
    position: relative;
  }
</style>
