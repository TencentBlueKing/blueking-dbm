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
    :width="200">
    <EditableSelect
      v-model="modelValue"
      :clearable="false">
      <BkOption
        v-for="(item, index) in selectList"
        :key="index"
        :disabled="item.disabled"
        :label="item.label"
        :value="item.value">
        <TextOverflowLayout>
          {{ item.label }}
          <template #append>
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
          </template>
        </TextOverflowLayout>
      </BkOption>
    </EditableSelect>
  </EditableColumn>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getClusterVersions } from '@services/source/redisToolbox';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { compareVersions } from '@utils';

  import { versionRegex } from '@/common/regex';

  interface Props {
    clusterIds: number[];
    currentVersions?: string[];
    nodeType: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const loading = ref(false);
  const targetVersionList = shallowRef<string[]>([]);

  const selectList = computed(() => {
    const currentVersionSorted = (props.currentVersions || [])
      .map((item) => (item.match(versionRegex) ? item.match(versionRegex)![0] : ''))
      .sort((a, b) => compareVersions(b, a));
    return targetVersionList.value.map((item) => ({
      disabled:
        currentVersionSorted.length === 0
          ? false
          : compareVersions(item.match(versionRegex) ? item.match(versionRegex)![0] : '', currentVersionSorted[0]) !==
            1,
      label: item,
      value: item,
    }));
  });

  watch(
    () => props.clusterIds,
    (newVal, oldVal) => {
      if (_.isEqual(newVal[0], oldVal?.[0])) {
        return;
      }
      if (props.clusterIds.length > 0 && props.nodeType) {
        loading.value = true;
        getClusterVersions({
          cluster_ids: props.clusterIds.join(','),
          node_type: props.nodeType,
          type: 'update',
        })
          .then((versions) => {
            if (oldVal && newVal[1] !== oldVal[1]) {
              modelValue.value = '';
            }
            nextTick(() => {
              const targetVersions = _.uniq(Object.values(versions).flatMap((item) => item));
              if (targetVersions.length && !modelValue.value) {
                [modelValue.value] = targetVersions;
              }
              targetVersionList.value = targetVersions;
            });
          })
          .finally(() => {
            loading.value = false;
          });
      } else {
        targetVersionList.value = [];
      }
    },
    {
      immediate: true,
    },
  );

  const isCurrentVersion = (value: string) => (props.currentVersions || []).includes(value);
</script>
