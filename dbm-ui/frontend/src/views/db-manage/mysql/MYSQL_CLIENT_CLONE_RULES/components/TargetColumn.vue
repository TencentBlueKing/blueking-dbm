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
    :label="t('新客户端IP')"
    :min-width="150"
    required>
    <EditableInput
      v-model="target"
      :placeholder="t('请输入管控区域:请输入IP，多个英文逗号分隔')" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { batchSplitRegex, ipv4 } from '@common/regex';

  interface Props {
    source: string;
  }

  const props = defineProps<Props>();

  const target = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('IP格式有误，请输入合法IP'),
      trigger: 'change',
      validator: (value: string) => _.every(value.split(batchSplitRegex), (item) => ipv4.test(_.trim(item))),
    },
    {
      message: t('ip数不能超过n个', { n: 500 }),
      trigger: 'blur',
      validator: (value: string) => value.split(batchSplitRegex).length <= 500,
    },
    {
      message: t('xx为源客户端IP', [props.source]),
      trigger: 'blur',
      validator: (value: string) => {
        if (!props.source) {
          return true;
        }
        return value.split(batchSplitRegex).every((ip) => ip !== props.source);
      },
    },
    {
      message: t('输入的IP重复'),
      trigger: 'blur',
      validator: (value: string) => {
        const hostList = value.split(batchSplitRegex).filter((item) => !!_.trim(item));
        if (_.uniq(hostList).length !== hostList.length) {
          return false;
        }
        return true;
      },
    },
  ];
</script>
