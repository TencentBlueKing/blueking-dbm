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
  <BkButton @click="handelShow">
    <DbIcon
      style="margin-right: 3px"
      :type="clusterInfo.domain ? 'edit' : 'add'" />
    <span>{{ clusterInfo.domain ? t('修改集群') : t('添加源集群') }}</span>
  </BkButton>
  <div
    v-if="clusterInfo.domain"
    class="mysql-openarea-source-cluster">
    {{ clusterInfo.domain }}（{{ clusterInfo.type === 'tendbha' ? t('主从') : t('单节点') }}）
    <DbIcon
      class="delete-icon"
      type="delete"
      @click="handleDelete" />
  </div>
  <ClusterSelector
    v-model:is-show="isShow"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    only-one-type
    :selected="selectedCluster"
    :tab-list-config="tabListConfig"
    @change="handelChange" />
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';

  const sourceClusterId = defineModel<number>({
    required: true,
  });

  const { t } = useI18n();

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: {
      multiple: false,
      showPreviewResultTitle: true,
    },
    [ClusterTypes.TENDBSINGLE]: {
      multiple: false,
      showPreviewResultTitle: true,
    },
  } as unknown as Record<string, TabConfig>;

  const clusterInfo = ref({
    domain: '',
    type: 'tendbha',
  });
  const isShow = ref(false);
  const selectedCluster = shallowRef<Record<string, TendbhaModel[]>>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  const handelShow = () => {
    isShow.value = true;
  };

  const handleDelete = () => {
    sourceClusterId.value = 0;
    clusterInfo.value = {
      domain: '',
      type: '',
    };
  };

  const handelChange = (selected: Record<string, TendbhaModel[]>) => {
    const selectList = Object.keys(selected).reduce((list: TendbhaModel[], key) => list.concat(...selected[key]), []);
    selectedCluster.value = selected;

    const { cluster_type: clusterType, id, master_domain: domain } = selectList[0];
    sourceClusterId.value = id;
    clusterInfo.value = {
      domain,
      type: clusterType,
    };
  };

  defineExpose({
    get() {
      return clusterInfo.value;
    },
    reset() {
      sourceClusterId.value = 0;
      clusterInfo.value = {
        domain: '',
        type: '',
      };
    },
    set(data: { domain: string; type: string }) {
      clusterInfo.value = data;
    },
  });
</script>
<style lang="less" scoped>
  .mysql-openarea-source-cluster {
    display: flex;
    margin-top: 12px;
    font-size: 14px;
    align-items: center;

    .delete-icon {
      font-size: 13px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
