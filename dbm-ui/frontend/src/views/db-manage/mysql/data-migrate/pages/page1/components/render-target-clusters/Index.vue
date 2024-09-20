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
    :rules="rules"
    :source-cluster-id="sourceClusterId" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { queryClusters } from '@services/source/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import { batchSplitRegex, domainRegex } from '@common/regex';

  import TableEditInput from './Input.vue';

  interface Props {
    sourceClusterId: number;
    data?: string;
  }

  interface Emits {
    (e: 'change', value: TendbhaModel[]): void;
  }

  interface Exposes {
    getValue: () => Promise<number[]>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
  });

  const emits = defineEmits<Emits>();

  const checkClusterExisted = async (value: string) => {
    const list = value.split(batchSplitRegex);
    return await queryClusters({
      cluster_filters: list.map((item) => ({
        immute_domain: item,
      })),
      bk_biz_id: currentBizId,
    }).then((data) => {
      if (data.length === list.length) {
        if (!ignoreEmitChange) {
          emits('change', data);
        }
        return true;
      }
      return false;
    });
  };

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const localValue = ref(props.data);
  const editRef = ref();
  const localClusterIds = ref<number[]>([]);

  let ignoreEmitChange = false;

  const rules = [
    {
      validator: (value: string) =>
        value
          .trim()
          .split('\n')
          .every((domain) => Boolean(domain)),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) => value.split('\n').every((domain) => domainRegex.test(domain)),
      message: t('目标集群输入格式有误'),
    },
    {
      validator: (value: string) => checkClusterExisted(value),
      message: t('目标集群不存在'),
    },
  ];

  watch(
    () => props.data,
    () => {
      if (!props.data) {
        return;
      }

      localValue.value = props.data;
      checkClusterExisted(props.data);
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      ignoreEmitChange = true;
      return editRef.value.getValue().then(() => {
        ignoreEmitChange = false;
        return localClusterIds.value;
      });
    },
  });
</script>
