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
        label="TendisPlus"
        name="tendisplus" />
      <BkTabPanel
        label="TendisSSD"
        name="tendisssd" />
    </BkTab>
    <div class="content-wrapper">
      <div class="mb-12">
        <BkButton
          class="w88"
          theme="primary"
          @click="handleShowOperation">
          {{ t('新建') }}
        </BkButton>
        <BkButton
          class="ml-8 w88"
          :disabled="tableSelectIdList.length < 1"
          @click="handleBatchRemove">
          {{ t('删除') }}
        </BkButton>
      </div>
      <DbTable
        ref="tableRef"
        :columns="tableColumn"
        :data-source="fetchDeployPlan"
        selectable
        @selection="handleTableSelection" />
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
      :cluster-type="clusterType"
      :data="operationData"
      :machine-type="activeMachineType"
      @change="handlePlanOperationChange" />
  </DbSideslider>
</template>
<script setup lang="tsx">
  import {
    computed,
    onMounted,
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import {
    batchRemoveDeployPlan,
    createDeployPlan,
    fetchDeployPlan,
    removeDeployPlan  } from '@services/dbResource';
  import type DeployPlanModel from '@services/model/db-resource/DeployPlan';

  import { ClusterTypes } from '@common/const';

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

  const tableColumn = [
    {
      label: t('方案名称'),
      field: 'name',
      fixed: 'left',
    },
    {
      label: t('集群分片数'),
      field: 'shard_cnt',
      width: 100,
    },
    {
      label: t('后端存储资源规格（机器数量）'),
      field: 'machine_pair_cnt',
      width: 250,
    },
    {
      label: t('集群预估容量（G）'),
      field: 'capacity',
      width: 150,
    },
    {
      label: t('更新时间'),
      field: 'update_at',
      width: 200,
    },
    {
      label: t('更新人'),
      field: 'updater',
      width: 150,
    },
    {
      label: t('操作'),
      width: 150,
      render: ({ data }: {data: DeployPlanModel}) => (
        <>
          <bk-button
            theme="primary"
            text
            onClick={() => handleEdit(data)}>
            {t('编辑')}
          </bk-button>
          <bk-button
            theme="primary"
            text
            class="ml-8"
            loading={Boolean(cloneLoadingMap.value[data.id])}
            onClick={() => handleClone(data)}>
            {t('克隆')}
          </bk-button>
          <span
            v-bk-tooltips={{
              content: t('该方案已被使用，无法删除'),
              disabled: !data.is_refer,
            }}>
            <bk-button
              theme="primary"
              class="ml-8"
              text
              disabled={data.is_refer}
              loading={Boolean(removeLoadingMap.value[data.id])}
              onClick={() => handleRemove(data)}>
              {t('删除')}
            </bk-button>
          </span>
        </>
      ),
    },
  ];

  const fetchData = () => {
    tableRef.value.fetchData({}, {
      cluster_type: clusterType.value,
    });
  };

  const handleTableSelection = (idList: number[]) => {
    tableSelectIdList.value = idList;
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
    }).then(() => {
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
      name: data.name,
      shard_cnt: data.shard_cnt,
      capacity: data.capacity,
      machine_pair_cnt: data.machine_pair_cnt,
      cluster_type: data.cluster_type,
      desc: data.desc,
      spec: data.spec,
    }).then(() => {
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
    }).then(() => {
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
