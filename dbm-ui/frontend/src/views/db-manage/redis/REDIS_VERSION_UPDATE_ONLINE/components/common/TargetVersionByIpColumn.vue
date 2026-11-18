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
    :loading="loading"
    required
    :width="300">
    <EditableSelect
      v-model="modelValue"
      :clearable="false">
      <DbOption
        v-for="item in versions"
        :id="item.db_version_id"
        :key="item.db_version_id"
        :name="item.version_name">
        <TextOverflowLayout>
          {{ item.version_name }}
          <template #append>
            <DbTag
              v-if="versionStageMap[item.phase]"
              class="ml-4"
              size="small"
              :theme="versionStageMap[item.phase].theme">
              {{ versionStageMap[item.phase].label }}
            </DbTag>
            <DbTag
              v-if="item.is_current"
              class="ml-4"
              size="small"
              theme="info">
              {{ t('当前版本') }}
            </DbTag>
            <DbTag
              v-if="item.recommend"
              class="ml-4"
              size="small"
              theme="warning">
              {{ t('推荐') }}
            </DbTag>
          </template>
        </TextOverflowLayout>
      </DbOption>
    </EditableSelect>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersionsByIp, type RedisUpgradeVersionItem } from '@services/source/redisToolbox';

  import { versionStageMap } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface Props {
    clusterId: number;
    ip: string;
    nodeType: string;
    versionName?: string; // 批量导入的版本名，候选加载后映射成 db_version_id
  }

  const props = defineProps<Props>();

  // 值为版本管理 V2 的 db_version_id
  const modelValue = defineModel<number>();

  const { t } = useI18n();

  const {
    data: versions,
    loading,
    run: runGetClusterVersionsByIp,
  } = useRequest<RedisUpgradeVersionItem[], [Parameters<typeof getClusterVersionsByIp>[0]]>(getClusterVersionsByIp, {
    manual: true,
    onSuccess(versionResult) {
      if (modelValue.value && versionResult.every((item) => item.db_version_id !== modelValue.value)) {
        modelValue.value = undefined;
      }
    },
  });

  watch(
    () => [props.ip, props.clusterId],
    () => {
      if (props.ip && props.clusterId) {
        runGetClusterVersionsByIp({
          cluster_id: props.clusterId,
          ip: props.ip,
          node_type: props.nodeType,
          type: 'update',
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [props.versionName, versions.value],
    () => {
      if (props.versionName && !modelValue.value && versions.value) {
        const matchItem = versions.value.find((item) => item.version_name === props.versionName);
        if (matchItem) {
          modelValue.value = matchItem.db_version_id;
        }
      }
    },
    {
      immediate: true,
    },
  );
</script>
