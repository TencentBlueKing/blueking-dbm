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
  <div class="cluster-instances">
    <p
      v-for="(inst, index) in renderData"
      :key="inst.bk_instance_id"
      class="pt-2 pb-2"
      :class="{ 'is-unavailable': inst.status === 'unavailable' }">
      <span class="pr-4">{{ inst.ip }}:{{ inst.port }}</span>
      <BkTag v-if="inst.status === 'unavailable'">
        {{ $t('不可用') }}
      </BkTag>
      <template v-if="index === 0">
        <i
          v-bk-tooltips="$t('复制')"
          class="db-icon-copy"
          @click="handleCopyInstances" />
      </template>
    </p>
    <template v-if="hasMore">
      <a
        class="cluster-instances__more"
        href="javascript:"
        @click="handleShowMore">
        {{ $t('查看更多') }}
      </a>
    </template>
  </div>
  <BkDialog
    v-model:is-show="dialogState.isShow"
    class="cluster-instances-dialog"
    :height="660"
    :title="title">
    <div class="cluster-instances-content">
      <div class="cluster-instances-content__operations mb-16">
        <BkButton
          class="mr-8"
          @click="handleCopyAbnormal">
          {{ $t('复制异常实例') }}
        </BkButton>
        <BkButton
          class="mr-8"
          @click="handleCopyAll">
          {{ $t('复制全部实例') }}
        </BkButton>
        <BkInput
          v-model="dialogState.keyword"
          clearable
          :placeholder="$t('搜索实例')"
          type="search"
          @clear="fetchInstance"
          @enter="fetchInstance" />
      </div>
      <DbTable
        ref="tableRef"
        :columns="columns"
        :data-source="getResourceInstances"
        fixed-pagination
        :height="440"
        @clear-search="handleClearSearch"
        @request-finished="handleRequestFinished" />
    </div>
    <template #footer>
      <BkButton @click="handleClose">
        {{ $t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getResourceInstances } from '@services/clusters';
  import type { ResourceInstance } from '@services/types/clusters';

  import { useCopy } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    ClusterInstStatusKeys,
    type ClusterTypeInfos,
    clusterTypeInfos,
    type DBTypesValues,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import { messageWarn } from '@utils';

  interface InstanceData {
    bk_instance_id: number,
    ip: string,
    name: string,
    port: number,
    status: string
  }

  interface DialogState {
    isShow: boolean,
    keyword: string,
    data: Array<ResourceInstance>,
  }

  interface Props {
    title: string,
    role: string,
    data: Array<InstanceData>;
    clusterId: number,
    clusterType?: ClusterTypeInfos
    // 部分集群接口不区分具体 cluster type，传 dbType，则代表 dbType、clusterType 均为 dbType 即可
    dbType?: DBTypesValues
  }
  const props = defineProps<Props>();

  const copy = useCopy();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();

  const tableRef = ref();
  const renderData = computed(() => props.data.slice(0, 10));
  const hasMore = computed(() => props.data.length > 10);

  const dialogState = reactive<DialogState>({
    isShow: false,
    keyword: '',
    data: [],
  });

  const columns = [{
    label: t('实例'),
    field: 'instance_address',
  }, {
    label: t('部署角色'),
    field: 'role',
  }, {
    label: t('状态'),
    field: 'status',
    render: ({ cell }: { cell: ClusterInstStatus }) => {
      const info = clusterInstStatus[cell] || clusterInstStatus.unavailable;
      return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
    },
  }, {
    label: t('部署时间'),
    field: 'create_at',
  }];

  const fetchInstanceParams = computed(() => {
    const params = { db_type: '', type: '' };
    if (props.dbType) {
      params.db_type = props.dbType;
      params.type = props.dbType;
    } else if (props.clusterType) {
      params.db_type = clusterTypeInfos[props.clusterType].dbType;
      params.type = props.clusterType;
    }
    return {
      ...params,
      bk_biz_id: globalBizsStore.currentBizId,
    };
  });


  /**
   * 获取节点列表
   */
  function fetchInstance() {
    nextTick(() => {
      tableRef.value.fetchData({
        ...fetchInstanceParams.value,
        cluster_id: props.clusterId,
        role: props.role,
      }, {
        instance_address: dialogState.keyword,
      });
    });
  }

  function handleShowMore() {
    dialogState.isShow = true;
    fetchInstance();
  }

  function handleClearSearch() {
    dialogState.keyword = '';
    fetchInstance();
  }

  function handleRequestFinished(data: ResourceInstance[]) {
    dialogState.data = data;
  }

  /**
   * 复制异常实例
   */
  function handleCopyAbnormal() {
    const abnormalInstances = dialogState.data
      .filter(item => item.status !== ClusterInstStatusKeys.RUNNING)
      .map(item => item.instance_address);
    if (abnormalInstances.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    copy(abnormalInstances.join('\n'));
  }

  /**
   * 复制所有实例
   */
  function handleCopyAll() {
    const instances = dialogState.data.map(item => item.instance_address);
    if (instances.length === 0) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    copy(instances.join('\n'));
  }

  function handleCopyInstances() {
    const { data } = props;
    const instances = data.map(item => `${item.ip}:${item.port}`);
    copy(instances.join('\n'));
  }

  function handleClose() {
    dialogState.isShow = false;
    dialogState.keyword = '';
    dialogState.data = [];
  }
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.cluster-instances {
  padding: 8px 0;

  .db-icon-copy {
    display: none;
    margin-top: 1px;
    margin-left: 4px;
    color: @primary-color;
    vertical-align: text-top;
    cursor: pointer;
  }

  .is-unavailable {
    color: #c4c6cc;

    .bk-tag {
      height: 20px;
      padding: 0 4px;
      line-height: 20px;
    }
  }

  &__more {
    display: inline-block;
    margin-top: 2px;
  }

  &-dialog {
    width: 80%;
    max-width: 1600px;
    min-width: 1200px;
  }

  &-content {
    &__operations {
      .flex-center();
    }
  }
}
</style>
