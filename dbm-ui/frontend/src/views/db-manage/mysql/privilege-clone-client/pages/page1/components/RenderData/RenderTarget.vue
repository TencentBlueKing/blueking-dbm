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
    v-model="localIpText"
    :disabled="!Boolean(source)"
    :placeholder="t('请输入IP，多个英文逗号分隔')"
    :rules="rules" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { ipv4 } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    source?: IDataRow['source'];
  }

  interface Exposes {
    getValue: () => Promise<{ [target: string]: string }>;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<IDataRow['target']>({
    default: [],
  });

  const splitReg = /[\n ,，;；]/;

  const { t } = useI18n();

  const inputRef = ref();
  const localIpText = ref('');
  const isRepeat = ref(false);

  const rules = [
    {
      validator: (value: string) => {
        const ipList = _.filter(value.split(splitReg), (item) => _.trim(item)) as Array<string>;
        return ipList.length > 0;
      },
      message: t('IP 不能为空'),
    },
    {
      validator: (value: string) => {
        const ipList = value.split(splitReg) as Array<string>;
        return _.every(ipList, (item) => ipv4.test(_.trim(item)));
      },
      message: t('IP格式不正确'),
    },
    {
      validator: (value: string) => value.split(splitReg).length <= 500,
      message: t('ip数不能超过n个', { n: 500 }),
      trigger: 'blur',
    },
    {
      validator: (value: string) => {
        if (!props.source) {
          return true;
        }
        const targets = value.split(splitReg).map((ip) => ip.trim());
        return targets.every((ip) => ip !== props.source!.ip);
      },
      message: t('xx为源客户端IP', [props.source?.ip]),
      trigger: 'blur',
    },
    {
      validator: (value: string) => {
        const hostList = value.split(splitReg).filter((item) => !!_.trim(item));
        if (_.uniq(hostList).length !== hostList.length) {
          isRepeat.value = true;
          return false;
        }
        isRepeat.value = false;
        return true;
      },
      message: t('输入的IP重复'),
    },
  ];

  // 同步外部主从机器
  watch(
    modelValue,
    () => {
      localIpText.value = modelValue.value.join(',');
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return inputRef.value
        .getValue()
        .then(() => ({
          target: localIpText.value.split(splitReg).join('\n'),
        }))
        .catch(() => ({
          target: '',
        }));
    },
  });
</script>
