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
    :append-rules="rules"
    field="dstCluster"
    :label="t('目标集群')"
    :loading="loading"
    :min-width="300"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :placeholder="t('请输入集群域名,多个请用分隔符分隔')"
        :title="t('目标集群')"
        type="textarea"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableTextarea
      v-model="localValue"
      :placeholder="t('请输入集群域名,多个请用分隔符分隔')"
      @change="handleInputChange">
      <template #append>
        <DbIcon
          class="batch-host-select"
          type="batch-host-select"
          @click="handleBatchSelect" />
      </template>
    </EditableTextarea>
  </EditableColumn>
  <!-- 批量选择 -->
  <ClusterSelector
    v-model:is-show="showBatchSelector"
    :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
    :selected="selectedClusters"
    :tab-list-config="tabListConfig"
    @change="handleBatchSelectorChange" />
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import { getHaClusterList } from '@services/source/sqlserveHaCluster';
  import { getSingleClusterList } from '@services/source/sqlserverSingleCluster';

  import { ClusterTypes } from '@common/const';
  import { batchSplitRegex, domainRegex } from '@common/regex';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    // 用于检查当前集群是否被包含在源集群中
    selectedMap: Record<string, boolean>;
    srcCluster: {
      cluster_type: ClusterTypes;
      id: number;
      major_version: string;
      master_domain: string;
    };
  }

  type Emits = (e: 'batch-edit', data: typeof modelValue.value, field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<
    {
      cluster_type: ClusterTypes;
      id?: number;
      major_version: string;
      master_domain: string;
    }[]
  >({
    default: () => [],
  });

  const { t } = useI18n();
  const showBatchEdit = ref(false);

  const compareVersion = (dstVersion: string, srcVersion: string) => {
    const versionMatchReg = /[^\d]*(\d+)$/;
    const [, dstversionNum] = dstVersion.match(versionMatchReg) || ['', ''];
    const [, srcVersionNum] = srcVersion.match(versionMatchReg) || ['', ''];

    return srcVersionNum > dstversionNum;
  };

  const tabListConfig = {
    [ClusterTypes.SQLSERVER_HA]: {
      disabledRowConfig: [
        {
          handler: (data: SqlServerHaModel) => data.isOffline,
          tip: t('集群已禁用'),
        },
        {
          handler: (data: SqlServerHaModel) => data.id === props.srcCluster.id,
          tip: t('不允许选择源集群'),
        },
        {
          handler: (data: SqlServerHaModel) => props.selectedMap[data.master_domain],
          tip: t('集群是已被选中的源集群'),
        },
        {
          handler: (data: SqlServerHaModel) => compareVersion(data.major_version, props.srcCluster.major_version),
          tip: t('不允许高版本往低版本迁移'),
        },
      ],
      id: ClusterTypes.SQLSERVER_HA,
      multiple: true,
      name: t('SqlServer 主从'),
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      disabledRowConfig: [
        {
          handler: (data: SqlServerSingleModel) => data.isOffline,
          tip: t('集群已禁用'),
        },
        {
          handler: (data: SqlServerHaModel) => data.id === props.srcCluster.id,
          tip: t('不允许选择源集群'),
        },
        {
          handler: (data: SqlServerHaModel) => props.selectedMap[data.master_domain],
          tip: t('集群是已被选中的源集群'),
        },
        {
          handler: (data: SqlServerSingleModel) => compareVersion(data.major_version, props.srcCluster!.major_version),
          tip: t('不允许高版本往低版本迁移'),
        },
      ],
      id: ClusterTypes.SQLSERVER_SINGLE,
      multiple: true,
      name: t('SqlServer 单节点'),
    },
  };

  const localValue = ref('');
  const loading = ref(false);
  const showBatchSelector = ref(false);
  const selectedClusters = computed<Record<string, SqlServerHaModel[]>>(() => ({
    [ClusterTypes.SQLSERVER_HA]: modelValue.value.filter(
      (item) => item.cluster_type === ClusterTypes.SQLSERVER_HA,
    ) as SqlServerHaModel[],
    [ClusterTypes.SQLSERVER_SINGLE]: modelValue.value.filter(
      (item) => item.cluster_type === ClusterTypes.SQLSERVER_SINGLE,
    ) as SqlServerHaModel[],
  }));

  let batchEditRowCount = 0;

  const rules = [
    {
      message: t('集群域名格式不正确'),
      trigger: 'change',
      validator: () => modelValue.value.every((item) => domainRegex.test(item.master_domain)),
    },
    {
      message: '',
      trigger: 'change',
      validator: () => {
        const conflictList: string[] = [];
        modelValue.value.forEach((item) => {
          if (props.selectedMap[item.master_domain]) {
            conflictList.push(item.master_domain);
          }
        });
        return conflictList.length > 0 ? t('集群xx是已被选中的源集群', [conflictList.join(',')]) : true;
      },
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: () => modelValue.value.every((item) => !!item.id),
    },
  ];

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchSelect = () => {
    showBatchSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    if (value) {
      loading.value = true;
      Promise.all([
        getHaClusterList({
          domain: value.split(batchSplitRegex).join(','),
          limit: -1,
        }),
        getSingleClusterList({
          domain: value.split(batchSplitRegex).join(','),
          limit: -1,
        }),
      ])
        .then((dataList) => {
          const temp: typeof modelValue.value = [];
          dataList.forEach((data) => {
            if (data.count) {
              temp.push(
                ...data.results.map((item) => ({
                  cluster_type: item.cluster_type,
                  id: item.id,
                  major_version: item.major_version,
                  master_domain: item.master_domain,
                })),
              );
            }
          });
          modelValue.value = temp;
        })
        .finally(() => {
          loading.value = false;
        });
    }
  };

  const handleBatchEditChange = (value: string | string[]) => {
    batchEditRowCount = Object.keys(props.selectedMap).length;
    handleInputChange(value as string);
  };

  const handleBatchSelectorChange = (selected: Record<string, SqlServerHaModel[]>) => {
    const data = [...selected[ClusterTypes.SQLSERVER_HA], ...selected[ClusterTypes.SQLSERVER_SINGLE]];
    modelValue.value = data.map((item) => ({
      cluster_type: item.cluster_type,
      id: item.id,
      major_version: item.major_version,
      master_domain: item.master_domain,
    }));
  };

  watch(
    modelValue,
    () => {
      localValue.value = modelValue.value.map((item) => item.master_domain).join('\n');
      if (batchEditRowCount) {
        emits('batch-edit', modelValue.value, 'dstCluster');
        batchEditRowCount--;
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .batch-host-select {
    font-size: 14px;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }
</style>
