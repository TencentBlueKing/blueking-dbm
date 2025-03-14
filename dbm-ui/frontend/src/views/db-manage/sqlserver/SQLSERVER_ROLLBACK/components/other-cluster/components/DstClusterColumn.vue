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
  <EditableColumn
    ref="editableTableColumn"
    :append-rules="rules"
    class="dst-cluster-column"
    field="dst_cluster.master_domain"
    :label="t('目标集群')"
    :loading="isLoading"
    :min-width="300"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :placeholder="t('请输入集群域名')"
        :title="t('目标集群')"
        type="input"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableInput
      v-model="modelValue.master_domain"
      class="column-input"
      :placeholder="t('请输入或选择集群')">
      <template #append>
        <div
          class="edit-btn-inner"
          @click.stop="handleShowClusterSelector">
          <DbIcon
            class="select-icon"
            type="host-select" />
        </div>
      </template>
    </EditableInput>
    <ClusterSelector
      v-model:is-show="isShowCellClusterSelector"
      :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
      only-one-type
      :selected="cellSelected"
      :tab-list-config="clusterSelectorTabConfig"
      @change="handleCellClusterChange" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import { filterClusters } from '@services/source/dbbase';

  import { ClusterTypes } from '@common/const';
  import { domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    srcClusterData: {
      bk_cloud_id: 0;
      id: 0;
      major_version: '';
      master_domain: '';
    };
  }

  type Emits = (e: 'batch-edit', value: string) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const modelValue = defineModel<Partial<ServiceReturnType<typeof filterClusters>[number]>>({
    required: true,
  });

  const compareVersion = (dstVersion: string, srcVersion: string) => {
    const versionMatchReg = /[^\d]*(\d+)$/;
    const [, dstversionNum] = dstVersion.match(versionMatchReg) || ['', ''];
    const [, srcVersionNum] = srcVersion.match(versionMatchReg) || ['', ''];

    return srcVersionNum > dstversionNum;
  };

  const { t } = useI18n();

  const isShowCellClusterSelector = ref(false);
  const showBatchEdit = ref(false);

  const clusterSelectorTabConfig = {
    [ClusterTypes.SQLSERVER_HA]: {
      disabledRowConfig: [
        {
          handler: (data: SqlServerHaModel) => data.isOffline,
          tip: t('集群已禁用'),
        },
        {
          handler: (data: SqlServerHaModel) => compareVersion(data.major_version, props.srcClusterData.major_version),
          tip: t('高版本不能恢复到低版本'),
        },
      ],
      id: ClusterTypes.SQLSERVER_HA,
      multiple: false,
      name: t('SqlServer 主从'),
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      disabledRowConfig: [
        {
          handler: (data: SqlServerSingleModel) => data.isOffline,
          tip: t('集群已禁用'),
        },
        {
          handler: (data: SqlServerSingleModel) =>
            compareVersion(data.major_version, props.srcClusterData!.major_version),
          tip: t('高版本不能恢复到低版本'),
        },
      ],
      id: ClusterTypes.SQLSERVER_SINGLE,
      multiple: false,
      name: t('SqlServer 单节点'),
    },
  };

  const rules = [
    {
      message: t('目标集群输入格式有误'),
      trigger: 'change',
      validator: (value: string) => domainRegex.test(value),
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: () => Boolean(modelValue.value.id),
    },
  ];

  const { loading: isLoading, run: runFilterClusters } = useRequest(filterClusters<SqlServerHaModel>, {
    manual: true,
    onSuccess(data) {
      if (data.length > 0) {
        [modelValue.value] = data;
      }
    },
  });

  const cellSelected = computed(() => {
    const selectedClusters: ComponentProps<typeof ClusterSelector>['selected'] = {
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
    };
    const { cluster_type: clusterType, id, master_domain: masterDomain } = modelValue.value;
    if (id && id > 0) {
      selectedClusters[clusterType!].push({
        id,
        master_domain: masterDomain,
      } as SqlServerHaModel);
    }
    return selectedClusters;
  });

  watch(
    () => modelValue.value.master_domain,
    () => {
      if (!modelValue.value.id && modelValue.value.master_domain) {
        modelValue.value.id = undefined;
        runFilterClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: modelValue.value.master_domain,
        });
      }
      if (!modelValue.value.master_domain) {
        modelValue.value.id = undefined;
      }
    },
    {
      immediate: true,
    },
  );

  const handleBatchEditChange = (value: string | string[]) => {
    emits('batch-edit', value as string);
  };

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleShowClusterSelector = () => {
    isShowCellClusterSelector.value = true;
  };

  const handleCellClusterChange = (selected: { [key: string]: Array<SqlServerHaModel> }) => {
    const list = Object.values(selected).filter((item) => item.length > 0);
    const [clusterData] = list[0];
    modelValue.value = clusterData;
  };
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .dst-cluster-column {
    .edit-btn-inner {
      display: flex;
      width: 24px;
      height: 24px;
      cursor: pointer;
      border-radius: 2px;
      align-items: center;
      justify-content: center;

      .select-icon {
        font-size: 16px;
        color: #979ba5;
      }

      &:hover {
        background: #f0f1f5;

        .select-icon {
          color: #3a84ff;
        }
      }
    }
  }
</style>
