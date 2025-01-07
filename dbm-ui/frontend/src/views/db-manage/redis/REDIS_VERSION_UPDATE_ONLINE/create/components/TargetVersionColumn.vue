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
    field="target_version"
    :label="t('目标版本')"
    required
    :width="200">
    <template
      v-if="batchSelectList.length"
      #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :data-list="batchSelectList"
        :title="t('目标版本')"
        type="select"
        @change="handleBatchEditChange">
        <BkButton
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          text
          theme="primary"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </BkButton>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :clearable="false">
      <BkOption
        v-for="(item, index) in selectList"
        :key="index"
        :label="item.label"
        :value="item.value">
        <div class="edit-spec-column-spec-item">
          <span class="text-overflow">
            {{ item.label }}
            <BkTag
              v-if="isCurrentVersion(item.label)"
              class="ml-4"
              size="small"
              theme="info">
              {{ t('当前版本') }}
            </BkTag>
            <BkTag
              v-if="index === 0"
              class="ml-4"
              size="small"
              theme="warning">
              {{ t('推荐') }}
            </BkTag>
          </span>
        </div>
      </BkOption>
    </EditableSelect>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getClusterVersions } from '@services/source/redisToolbox';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    tableData: {
      cluster: {
        id: number;
        cluster_type: string;
      };
      node_type: string;
    }[];
    params: {
      clusterId: number;
      nodeType: string;
    };
    currentVersions?: string[];
  }

  interface Emits {
    (e: 'batch-edit', value: string, field: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const isShowBatchEdit = ref(false);

  const batchSelectList = shallowRef<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const selectList = shallowRef<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const versionListParams = computed(() => {
    if (!props.tableData[0].cluster.id) {
      return null;
    }
    const [firstRow, ...otherRowList] = props.tableData;
    const params = {
      nodeType: firstRow.node_type,
      clusterId: firstRow.cluster.id,
    };
    if (
      otherRowList.length === 0 ||
      otherRowList.every(
        (rowItem) =>
          rowItem.cluster.cluster_type === firstRow.cluster.cluster_type && rowItem.node_type === firstRow.node_type,
      )
    ) {
      return params;
    }
    return null;
  });

  watch(versionListParams, () => {
    if (versionListParams.value?.clusterId && versionListParams.value.nodeType) {
      getClusterVersions({
        node_type: versionListParams.value.nodeType,
        type: 'update',
        cluster_id: versionListParams.value.clusterId,
      }).then((versions) => {
        batchSelectList.value = versions.map((item) => ({
          label: item,
          value: item,
        }));
      });
    } else {
      batchSelectList.value = [];
    }
  });

  watch(
    () => [props.params.clusterId, props.params.nodeType],
    () => {
      if (props.params.clusterId && props.params.nodeType) {
        getClusterVersions({
          node_type: props.params.nodeType,
          type: 'update',
          cluster_id: props.params.clusterId,
        }).then((versions) => {
          if (versions.length && !modelValue.value) {
            [modelValue.value] = versions;
          }
          selectList.value = versions.map((item) => ({
            label: item,
            value: item,
          }));
        });
      } else {
        selectList.value = [];
      }
    },
    {
      immediate: true,
    },
  );

  const isCurrentVersion = (value: string) => (props.currentVersions || []).includes(value);

  const handleBatchEditShow = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string | string[]) => {
    emits('batch-edit', value as string, 'target_version');
  };
</script>
