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
    :label="t('规格')"
    :min-width="150">
    <EditableSelect
      v-model="modelValue"
      display-key="spec_name"
      id-key="spec_id"
      :list="specList" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { ClusterTypes } from '@common/const';

  const modelValue = defineModel<number>({
    required: false,
  });

  const { t } = useI18n();

  const specList = ref<ServiceReturnType<typeof getResourceSpecList>['results']>([]);

  useRequest(getResourceSpecList, {
    defaultParams: [
      {
        enable: true,
        spec_cluster_type: ClusterTypes.TENDBCLUSTER,
      },
    ],
    onSuccess: (data) => {
      specList.value = data.results;
    },
  });
</script>
