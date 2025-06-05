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
    field="db_version"
    :label="label || t('目标版本')"
    required
    :width="200">
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
  import { useRequest } from 'vue-request';

  import { listPackages } from '@services/source/package';

  import { DBTypes } from '@common/const';

  import { QueryKeyMap } from '@views/db-manage/redis/common/const';

  interface Props {
    clusterType?: string;
    currentVersions?: string[];
    label?: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const selectList = shallowRef<
    {
      label: string;
      value: string;
    }[]
  >([]);

  const { run: runListPackagesForSelect } = useRequest(listPackages, {
    manual: true,
    onSuccess(listResult) {
      selectList.value = listResult.map((value) => ({
        label: value,
        value,
      }));
    },
  });

  watch(
    () => props.clusterType,
    () => {
      if (props.clusterType) {
        runListPackagesForSelect({
          db_type: DBTypes.REDIS,
          query_key: QueryKeyMap[props.clusterType],
        });
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.currentVersions,
    () => {
      if (props.currentVersions?.length === 1 && !modelValue.value) {
        [modelValue.value] = props.currentVersions;
      }
    },
  );

  const isCurrentVersion = (value: string) => (props.currentVersions || []).includes(value);
</script>
