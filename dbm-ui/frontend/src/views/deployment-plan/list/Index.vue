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
  <div class="deployment-plan-list-page">
    <BkTab
      :active="activeMachineType"
      class="header-tab"
      type="unborder-card"
      @change="handleClusterChange">
      <BkTabPanel
        label="TendisCache"
        name="tendiscache" />
      <BkTabPanel
        label="Tendisplus"
        name="tendisplus" />
      <BkTabPanel
        label="TendisSSD"
        name="tendisssd" />
    </BkTab>
    <div class="content-wrapper">
      <div class="mb-12">
        <BkButton
          class="w-88"
          theme="primary"
          @click="handleShowOperation">
          {{ t('新建') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          :disabled="tableSelectIdList.length < 1"
          @click="handleBatchRemove">
          {{ t('删除') }}
        </BkButton>
      </div>
      <DbTable
        ref="tableRef"
        :data-source="fetchDeployPlan"
        row-key="id"
        selectable
        @selection="handleTableSelection">
        <TableColumn
          col-key="name"
          fixed="left"
          :min-width="200"
          :title="t('方案名称')">
        </TableColumn>
        <TableColumn
          col-key="shard_cnt"
          :title="t('集群分片数')"
          :width="100">
        </TableColumn>
        <TableColumn
          col-key="machine_pair_cnt"
          :title="t('后端存储资源规格（机器数量）')"
          :width="250">
        </TableColumn>
        <TableColumn
          col-key="capacity"
          :title="t('集群预估容量（G）')"
          :width="150">
        </TableColumn>
        <TableColumn
          col-key="update_at"
          :title="t('更新时间')"
          :width="200">
        </TableColumn>
        <TableColumn
          col-key="updater"
          :title="t('更新人')"
          :width="150">
        </TableColumn>
        <TableColumn
          col-key="row-operation"
          :title="t('操作')"
          :width="150">
          <template #default="{ row: data }: { row: DeployPlanModel }">
            <BkButton
              text
              theme="primary"
              @click="handleEdit(data)">
              {{ t('编辑') }}
            </BkButton>
            <BkButton
              class="ml-8"
              :loading="Boolean(cloneLoadingMap[data.id])"
              text
              theme="primary"
              @click="handleClone(data)">
              {{ t('克隆') }}
            </BkButton>
            <span
              v-bk-tooltips="{
                content: t('该方案已被使用，无法删除'),
                disabled: !data.is_refer,
              }">
              <BkButton
                class="ml-8"
                :disabled="data.is_refer"
                :loading="Boolean(removeLoadingMap[data.id])"
                text
                theme="primary"
                @click="handleRemove(data)">
                {{ t('删除') }}
              </BkButton>
            </span>
          </template>
        </TableColumn>
      </DbTable>
    </div>
  </div>
  <DbSideslider
    v-model:is-show="isShowOperation"
    width="960">
    <template #header>
      <span>{{ t('新建方案') }}</span>
      <BkTag
        class="ml-8"
        theme="info">
        {{ activeMachineType }}
      </BkTag>
    </template>
    <PlanOperation
      cluster-type="redis"
      :data="operationData"
      :machine-type="clusterType"
      @change="handlePlanOperationChange" />
  </DbSideslider>
</template>
<script setup lang="tsx">
  import { computed, onMounted, ref, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type DeployPlanModel from '@services/model/db-resource/DeployPlan';
  import {
    batchRemoveDeployPlan,
    createDeployPlan,
    fetchDeployPlan,
    removeDeployPlan,
  } from '@services/source/dbresourceDeployPlan';

  import { ClusterTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { messageSuccess } from '@utils';

  import PlanOperation from './components/Operation.vue';

  const { t } = useI18n();

  const tableRef = ref();
  const activeMachineType = ref('TendisCache');
  const isShowOperation = ref(false);
  const isBatchRemoveing = ref(false);
  const operationData = shallowRef();
  const tableSelectIdList = shallowRef<number[]>([]);
  const cloneLoadingMap = shallowRef<Record<number, boolean>>({});
  const removeLoadingMap = shallowRef<Record<number, boolean>>({});

  const clusterType = computed(() => {
    const typeMap = {
      tendiscache: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      tendisplus: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
      tendisssd: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
    } as Record<string, string>;
    return typeMap[activeMachineType.value];
  });

  const fetchData = () => {
    tableRef.value.fetchData({
      cluster_type: clusterType.value,
    });
  };

  const handleTableSelection = (idList: string[], list: DeployPlanModel[]) => {
    tableSelectIdList.value = list.map((item) => item.id);
  };
  const handleClusterChange = (value: string) => {
    activeMachineType.value = value;
    fetchData();
  };

  // 新建
  const handleShowOperation = () => {
    isShowOperation.value = true;
    operationData.value = undefined;
  };

  // 批量删除
  const handleBatchRemove = () => {
    isBatchRemoveing.value = true;
    batchRemoveDeployPlan({
      deploy_plan_ids: tableSelectIdList.value,
    })
      .then(() => {
        fetchData();
      })
      .finally(() => {
        isBatchRemoveing.value = false;
      });
  };

  // 编辑
  const handleEdit = (data: DeployPlanModel) => {
    isShowOperation.value = true;
    operationData.value = data;
  };

  // 克隆
  const handleClone = (data: DeployPlanModel) => {
    cloneLoadingMap.value = {
      ...cloneLoadingMap.value,
      [data.id]: true,
    };
    createDeployPlan({
      capacity: data.capacity,
      cluster_type: data.cluster_type,
      desc: data.desc,
      machine_pair_cnt: data.machine_pair_cnt,
      name: data.name,
      shard_cnt: data.shard_cnt,
      spec: data.spec,
    })
      .then(() => {
        fetchData();
        messageSuccess(t('部署方案克隆成功'));
      })
      .finally(() => {
        cloneLoadingMap.value = {
          ...cloneLoadingMap.value,
          [data.id]: false,
        };
      });
  };

  // 操作成功需要刷新页面
  const handlePlanOperationChange = () => {
    fetchData();
  };

  const handleRemove = (data: DeployPlanModel) => {
    removeLoadingMap.value = {
      ...removeLoadingMap.value,
      [data.id]: true,
    };
    removeDeployPlan({
      id: data.id,
    })
      .then(() => {
        fetchData();
        messageSuccess(t('删除成功'));
      })
      .finally(() => {
        removeLoadingMap.value = {
          ...removeLoadingMap.value,
          [data.id]: true,
        };
      });
  };

  onMounted(() => {
    fetchData();
  });
</script>
<style lang="less">
  .deployment-plan-list-page {
    display: block;
    margin: -24px;

    .header-tab {
      z-index: 99;
      padding: 0 24px;
      background: #fff;

      .bk-tab-content {
        display: none;
      }
    }

    .content-wrapper {
      padding: 24px;
    }
  }
</style>
