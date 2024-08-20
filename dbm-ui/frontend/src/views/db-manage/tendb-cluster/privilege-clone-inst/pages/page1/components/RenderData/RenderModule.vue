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
  <TableEditInput
    ref="inputRef"
    :model-value="source?.dbModuleName"
    :placeholder="t('输入集群后自动生成')"
    readonly
    :rules="rules" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TableEditInput from '@views/db-manage/tendb-cluster/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    source: IDataRow['source'];
  }

  interface Exposes {
    getValue: () => Promise<Record<'module', number>>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const inputRef = ref();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('源实例不能为空'),
    },
  ];

  defineExpose<Exposes>({
    getValue() {
      return inputRef.value
        .getValue()
        .then(() => ({
          module: props.source!.dbModuleId,
        }))
        .catch(() =>
          Promise.reject({
            module: props.source!.dbModuleId,
          }),
        );
    },
  });
</script>
