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
    :disabled-method="disabledMethod"
    field="db_version"
    :label="t('Redis版本')"
    :min-width="150"
    required>
    <EditableSelect
      v-model="modelValue"
      :input-search="false"
      :list="versionList"
      :placeholder="t('自动生成')">
      <template #option="{ item, index }">
        <div>
          {{ item.label }}
          <BkTag
            v-if="modelValue === item.value"
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
        </div>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersions } from '@services/source/redisToolbox';

  interface Props {
    cluster: {
      id: number;
      major_version: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const versionList = ref<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const { run: fetchVersions } = useRequest(getClusterVersions, {
    manual: true,
    onSuccess(versions) {
      if (!versions.length) {
        return;
      }
      versionList.value = versions.map((item) => ({
        label: item,
        value: item,
      }));
      let currentVersion = '';
      versions.forEach((item) => {
        if (item.indexOf(props.cluster.major_version.toLocaleLowerCase()) > -1) {
          currentVersion = item;
        }
      });
      modelValue.value = currentVersion || versions[0];
    },
  });

  watch(
    () => props.cluster,
    () => {
      if (props.cluster.id) {
        fetchVersions({
          cluster_id: props.cluster.id,
          node_type: 'Backend',
          type: 'update',
        });
      }
    },
    {
      immediate: true,
    },
  );

  const disabledMethod = (rowData?: any, field?: string) => {
    if (field === 'db_version' && !rowData.cluster.id) {
      return t('请先选择集群');
    }
    return '';
  };
</script>
