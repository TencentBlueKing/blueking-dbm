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
    ref="editRef"
    v-model="localValue"
    :placeholder="t('请输入或选择集群')"
    :rules="rules" />
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { filterClusters } from '@services/source/dbbase';

  import { useGlobalBizs } from '@stores';

  import { domainRegex } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  interface Props {
    data?: string;
    inputed?: string[];
  }

  interface Emits {
    (e: 'inputFinish', value: TendbhaModel): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    inputed: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const localValue = ref(props.data);
  const editRef = ref<InstanceType<typeof TableEditInput>>();
  // 记录最近输入
  let recentValue: string = props.data || '';

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => domainRegex.test(value),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: async (value: string) => {
        const realValue = _.trim(value);
        localValue.value = realValue;
        const listResult = await filterClusters({ bk_biz_id: currentBizId, exact_domain: realValue });
        if (listResult.length) {
          emits('inputFinish', listResult[0] as unknown as TendbhaModel);
        }
        return listResult.length > 0;
      },
      message: t('目标集群不存在'),
    },
    {
      validator: (value: string) => {
        if (value === recentValue) {
          return true;
        }
        recentValue = value;
        return !props.inputed.includes(value);
      },
      message: t('目标集群重复'),
    },
  ];
</script>
