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
  <BkLoading :loading="loading">
    <TableEditSelect
      ref="selectRef"
      v-model="localValue"
      :list="targetVersionList"
      :placeholder="t('请选择')"
      :rules="rules">
      <template #suffix="{ item, index }">
        <div>
          <BkTag
            v-if="isCurrentVersion(item.label as string)"
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
    </TableEditSelect>
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersions } from '@services/source/redisToolbox';

  import TableEditSelect, { type IListItem } from '@views/db-manage/redis/common/edit/Select.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    data: IDataRow;
    currentList?: string[];
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = withDefaults(defineProps<Props>(), {
    currentList: () => [],
  });

  const { t } = useI18n();

  const selectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localValue = ref('');
  const targetVersionList = ref<IListItem[]>([]);

  const { loading, run: fetchTargetClusterVersions } = useRequest(getClusterVersions, {
    manual: true,
    onSuccess(versions) {
      targetVersionList.value = versions.map((item) => ({
        label: item,
        value: item,
      }));
    },
  });

  const rules = [
    {
      validator: (value: string) => !!value,
      message: t('请选择版本'),
    },
  ];

  watch(
    () => [props.data.clusterId, props.data.nodeType],
    () => {
      if (props.data.clusterId) {
        fetchTargetClusterVersions({
          node_type: props.data.nodeType,
          type: 'update',
          // cluster_type: props.data.clusterType,
          cluster_id: props.data.clusterId,
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.currentList,
    () => {
      if (props.currentList.length > 0) {
        targetVersionList.value = targetVersionList.value.map((item) => ({
          label: item.label,
          value: item.value,
          disabled: props.currentList.every((value) => value === item.value),
        }));
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    targetVersionList,
    () => {
      localValue.value = '';
      if (targetVersionList.value.length > 0) {
        const currentVersion = targetVersionList.value[0].value as string;
        localValue.value = currentVersion;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.data.targetVersion,
    () => {
      localValue.value = props.data?.targetVersion ? props.data?.targetVersion : '';
    },
    {
      immediate: true,
    },
  );

  const isCurrentVersion = (value: string) => props.currentList.includes(value);

  defineExpose<Exposes>({
    getValue() {
      return selectRef
        .value!.getValue()
        .then(() => localValue.value)
        .catch(() => Promise.reject(localValue.value));
    },
  });
</script>
