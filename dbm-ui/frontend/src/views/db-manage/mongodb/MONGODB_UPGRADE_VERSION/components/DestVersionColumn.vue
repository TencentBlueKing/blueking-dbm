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
    :disabled-method="() => (!cluster.id ? t('请先输入合法的集群域名') : false)"
    field="dest_version"
    :label="t('目标版本')"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :data-list="batchVersionList"
        :title="t('目标版本')"
        type="select"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleShowBatchEdit">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :clearable="false">
      <BkOptionGroup
        v-for="group in groupedVersions"
        :key="group.label"
        :label="group.label">
        <BkOption
          v-for="version in group.children"
          :key="version.value"
          :label="version.value"
          :value="version.value" />
      </BkOptionGroup>
    </EditableSelect>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listAvailableMongoVersions } from '@services/source/mongodbToolbox';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  export interface VersionGroup {
    children: { label: string; value: string }[];
    label: string;
  }

  export type VersionData = { full_list: string[]; major: string }[];

  interface Props {
    batchVersionList: VersionGroup[];
    cluster: {
      id: number;
    };
  }

  const props = defineProps<Props>();

  const emits = defineEmits<{
    (e: 'batch-edit', value: string, field: string): void;
    (e: 'request-success', clusterId: number, data: VersionData): void;
  }>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const isShowBatchEdit = ref(false);
  const groupedVersions = ref<VersionGroup[]>([]);

  const { run: fetchVersions } = useRequest(listAvailableMongoVersions, {
    manual: true,
    onSuccess(data) {
      groupedVersions.value = data.map((group) => ({
        children: group.full_list.map((version) => ({ label: version, value: version })),
        label: group.major,
      }));
      emits('request-success', props.cluster.id, data);
    },
  });

  watch(
    () => props.cluster.id,
    (id) => {
      if (id) {
        fetchVersions({ cluster_ids: [id] });
      }
    },
  );

  watch(
    modelValue,
    () => {
      const allValues = groupedVersions.value.flatMap((group) => group.children.map((item) => item.value));
      if (allValues.length > 0 && !allValues.includes(modelValue.value)) {
        modelValue.value = '';
      }
    },
    { immediate: true },
  );

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string) => {
    emits('batch-edit', value, 'dest_version');
  };
</script>

<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
