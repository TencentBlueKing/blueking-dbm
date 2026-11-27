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
  <ClusterColumn
    v-model="modelValue"
    field="target_cluster.master_domain"
    :label="t('目标集群')"
    :min-width="minWidth"
    :selected="selected"
    :tab-list-config="tabListConfig"
    @batch-edit="handleBatchEdit" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';

  import { ClusterTypes } from '@common/const';

  import type { TabConfig } from '@components/cluster-selector/Index.vue';

  import ClusterColumn from '@views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue';

  interface ClusterInfo {
    cluster_type: string;
    cluster_type_name?: string;
    id: number;
    master_domain: string;
  }

  interface Props {
    minWidth?: number;
    selected: ClusterInfo[];
    sourceCluster: ClusterInfo;
  }

  type Emits = (e: 'batch-edit', value: MongodbModel[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    minWidth: 350,
  });
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<ClusterInfo>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = computed(
    () =>
      ({
        [ClusterTypes.MONGO_REPLICA_SET]: {
          disabledRowConfig: [
            {
              handler: (data: MongodbModel) => data.id === props.sourceCluster.id,
              tip: t('不能选择源集群'),
            },
          ],
          showPreviewResultTitle: true,
        },
        [ClusterTypes.MONGO_SHARED_CLUSTER]: {
          disabledRowConfig: [
            {
              handler: (data: MongodbModel) => data.id === props.sourceCluster.id,
              tip: t('不能选择源集群'),
            },
          ],
          showPreviewResultTitle: true,
        },
      }) as unknown as Record<string, TabConfig>,
  );

  const handleBatchEdit = (clusterList: MongodbModel[]) => {
    emits('batch-edit', clusterList);
  };
</script>
