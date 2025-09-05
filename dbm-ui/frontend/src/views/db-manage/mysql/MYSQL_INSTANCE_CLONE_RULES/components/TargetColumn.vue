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
    :append-rules="rules"
    field="target"
    :label="t('新实例')"
    :min-width="150"
    required>
    <EditableInput
      v-model="target"
      :placeholder="t('请输入IP_Port')" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { ipPort } from '@common/regex';

  interface Props {
    source: string;
    tableData: {
      target: string;
    }[];
  }

  const props = defineProps<Props>();

  const target = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('实例格式有误，请输入 IP:Port'),
      trigger: 'change',
      validator: (value: string) => !value || ipPort.test(_.trim(value)),
    },
    {
      message: t('xx为源实例', [props.source]),
      trigger: 'blur',
      validator: (value: string) => !props.source || !value || value !== props.source,
    },
    {
      message: t('输入的实例重复'),
      trigger: 'blur',
      validator: (value: string) => !value || props.tableData.filter((item) => item.target === value).length < 2,
    },
  ];
</script>
