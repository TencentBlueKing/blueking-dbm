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
  <TableColumn
    col-key="podName"
    fixed="left"
    :min-width="200"
    :title="t('实例')">
    <template #default="{ row }: { row: IColumnData }">
      <TextOverflowLayout>
        <BkButton
          text
          theme="primary"
          @click="handleInstanceAddressClick(row)">
          {{ row.podName }}
        </BkButton>
      </TextOverflowLayout>
      <div>
        <span style="color: #979ba5">{{ row.node }}</span>
        <!-- <BkTag
          class="ml-4"
          size="small"
          theme="info">
          Leader
        </BkTag> -->
      </div>
    </template>
  </TableColumn>
  <InfoSideslider
    v-if="data"
    v-model="isShowInfoSideslider"
    :cluster-data="clusterData"
    :cluster-type="clusterType"
    :data="data"
    :role="role" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import SurrealdbHaInstanceModel from '@services/model/surrealdb/surrealdb-ha-instance';
  import SurrealdbSingleInstanceModel from '@services/model/surrealdb/surrealdb-single-instance';

  import { ClusterTypes } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';

  import QdrantHaInstanceModel from '@/services/model/qdrant/qdrant-ha-instance';

  import InfoSideslider from './components/info-sideslider/Index.vue';

  interface ClusterTypeRelateClusterModel {
    [ClusterTypes.K8S_QDRANT_HA]: QdrantHaInstanceModel;
    [ClusterTypes.K8S_SURREALDB_HA]: SurrealdbHaInstanceModel;
    [ClusterTypes.K8S_SURREALDB_SINGLE]: SurrealdbSingleInstanceModel;
  }

  type IColumnData = ServiceReturnType<
    ReturnType<typeof useClusterInstanceList<keyof ClusterTypeRelateClusterModel>>
  >['results'][number];

  interface Props {
    clusterData: {
      cluster_name: string;
      db_type: string;
      id: number;
      k8s_cluster_name: string;
      namespace: string;
    };
    clusterType: keyof ClusterTypeRelateClusterModel;
    role: string;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const isShowInfoSideslider = ref(false);
  const data = shallowRef<IColumnData>();

  const handleInstanceAddressClick = (row: IColumnData) => {
    isShowInfoSideslider.value = true;
    data.value = row;
  };
</script>
