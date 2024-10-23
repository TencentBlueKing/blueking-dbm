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
    v-model="localValue"
    :placeholder="t('请输入或选择集群')"
    :rules="rules" />
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { quickSearch } from '@services/source/quickSearch';

  import { domainRegex } from '@common/regex';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  export type ClusterModel = ServiceReturnType<typeof quickSearch>['cluster_domain'][number];

  interface Props {
    data: string;
    inputed?: string[];
  }

  interface Emits {
    (e: 'loading', value: boolean): void;
    (e: 'inputFinish', value: ClusterModel): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    inputed: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localValue = ref(props.data);

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
      validator: (value: string) => props.inputed.filter((item) => item === value).length <= 1,
      message: t('目标集群重复'),
    },
    {
      validator: async (value: string) => {
        emits('loading', true);
        const { cluster_domain: clusters } = await quickSearch({
          bk_biz_ids: [],
          db_types: [],
          resource_types: [],
          filter_type: 'EXACT',
          keyword: _.trim(value),
        });
        if (clusters.length) {
          emits('inputFinish', clusters[0]);
        }
        emits('loading', false);
        return clusters.length > 0;
      },
      message: t('目标集群不存在'),
    },
  ];
</script>
