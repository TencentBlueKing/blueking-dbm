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
  <div class="render-data">
    <RenderTable>
      <template #default>
        <RenderTableHeadColumn
          :min-width="120"
          :width="450">
          <span>{{ t('目标集群') }}</span>
          <template #append>
            <BkPopover
              :content="t('批量添加')"
              theme="dark">
              <span
                class="batch-edit-btn"
                @click="handleShowBatchSelector">
                <DbIcon type="batch-host-select" />
              </span>
            </BkPopover>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="110"
          :required="false"
          :width="150">
          <span>{{ t('架构版本') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="150"
          :width="300">
          <span>{{ t('节点类型') }}</span>
          <template #append>
            <BatchEditColumn
              v-model="batchEditShow.nodeType"
              :data-list="selectList"
              :title="t('节点类型')"
              @change="(value) => handleBatchEditChange(value, 'nodeType')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('nodeType')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :required="false"
          :width="300">
          <span>{{ t('当前使用的版本') }}</span>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          :min-width="100"
          :width="300">
          <span>{{ t('目标版本') }}</span>
          <template
            v-if="targetVersionList.length"
            #append>
            <BatchEditColumn
              v-model="batchEditShow.targetVersion"
              :data-list="targetVersionList"
              :title="t('目标版本')"
              @change="(value) => handleBatchEditChange(value, 'targetVersion')">
              <span
                v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
                class="batch-edit-btn"
                @click="handleBatchEditShow('targetVersion')">
                <DbIcon type="bulk-edit" />
              </span>
            </BatchEditColumn>
          </template>
        </RenderTableHeadColumn>
        <RenderTableHeadColumn
          fixed="right"
          :required="false"
          :width="100">
          {{ t('操作') }}
        </RenderTableHeadColumn>
      </template>
      <template #data>
        <slot />
      </template>
    </RenderTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersions } from '@services/source/redisToolbox';

  import RenderTableHeadColumn from '@components/render-table/HeadColumn.vue';
  import RenderTable from '@components/render-table/Index.vue';

  // import { getClusterVersions } from '@services/source/redisToolbox';
  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  import type { IDataRow, IDataRowBatchKey } from './Row.vue';

  interface Props {
    versionListParams: Pick<IDataRow, 'nodeType' | 'clusterId'> | null;
  }

  interface Emits {
    (e: 'showBatchSelector'): void;
    (e: 'batchEdit', value: string | string[], filed: IDataRowBatchKey): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const targetVersionList = ref<
    {
      value: string;
      label: string;
    }[]
  >([]);
  const batchEditShow = reactive({
    nodeType: false,
    targetVersion: false,
  });

  const selectList = [
    {
      value: 'Proxy',
      label: 'Proxy',
    },
    {
      value: 'Backend',
      label: 'Backend',
    },
  ];

  const { run: fetchTargetClusterVersions } = useRequest(getClusterVersions, {
    manual: true,
    onSuccess(versions) {
      targetVersionList.value = versions.map((item) => ({
        label: item,
        value: item,
      }));
    },
  });

  watch(
    () => props.versionListParams,
    () => {
      if (props.versionListParams) {
        fetchTargetClusterVersions({
          node_type: props.versionListParams.nodeType,
          type: 'update',
          cluster_id: props.versionListParams.clusterId,
        });
      } else {
        targetVersionList.value = [];
      }
    },
  );

  const handleShowBatchSelector = () => {
    emits('showBatchSelector');
  };

  const handleBatchEditShow = (key: IDataRowBatchKey) => {
    batchEditShow[key] = !batchEditShow[key];
  };

  const handleBatchEditChange = (value: string | string[], filed: IDataRowBatchKey) => {
    emits('batchEdit', value, filed);
  };
</script>
<style lang="less">
  .render-data {
    .batch-edit-btn {
      margin-left: 4px;
      color: #3a84ff;
      cursor: pointer;
    }
  }
</style>
