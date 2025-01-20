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
    :label="t('目标版本')"
    required
    :width="200">
    <BkLoading
      :loading="listPackagesLoading"
      style="width: 100%">
      <EditableSelect
        v-model="modelValue"
        :clearable="false">
        <BkOption
          v-for="(item, index) in selectList"
          :key="index"
          :label="item.label"
          :value="item.value">
          <div>
            {{ item.label }}
            <BkTag
              v-if="index === 0"
              class="ml-4"
              size="small"
              theme="warning">
              {{ t('推荐') }}
            </BkTag>
          </div>
        </BkOption>
      </EditableSelect>
    </BkLoading>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listPackages } from '@services/source/package';

  import { QueryKeyMap } from '@views/db-manage/redis/common/const';

  interface Props {
    targetClusterType?: string;
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

  const { loading: listPackagesLoading, run: runListPackages } = useRequest(listPackages, {
    manual: true,
    onSuccess(listResult) {
      selectList.value = listResult.map((value) => ({
        label: value,
        value,
      }));
      if (!modelValue.value && listResult.length > 0) {
        modelValue.value = listResult[0];
      }
    },
  });

  watch(
    () => props.targetClusterType,
    () => {
      if (props.targetClusterType) {
        modelValue.value = '';
        runListPackages({
          db_type: 'redis',
          query_key: QueryKeyMap[props.targetClusterType],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
