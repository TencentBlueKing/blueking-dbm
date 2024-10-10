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
  <RenderText
    ref="editInputRef"
    :data="localInstanceData?.master_domain"
    :is-loading="isLoading"
    :placeholder="t('根据实例生成')" />
</template>
<script setup lang="ts">
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkMysqlInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    slave?: IDataRow['slave'];
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const editInputRef = ref();
  const localInstanceData = shallowRef<ServiceReturnType<typeof checkMysqlInstances>[0]>();

  const { loading: isLoading, run: fetchCheckMysqlInstances } = useRequest(checkMysqlInstances, {
    manual: true,
    onSuccess(data) {
      [localInstanceData.value] = data;
    },
  });

  watch(
    () => props.slave,
    () => {
      if (!props.slave) {
        localInstanceData.value = undefined;
        return;
      }
      fetchCheckMysqlInstances({
        bizId: currentBizId,
        instance_addresses: [props.slave.instanceAddress],
      });
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return editInputRef.value
        .getValue()
        .then(() => {
          if (!localInstanceData.value) {
            return Promise.reject();
          }
          return {
            cluster_id: localInstanceData.value.cluster_id,
          };
        })
        .catch(() => Promise.reject({ cluster_id: localInstanceData.value?.cluster_id }));
    },
  });
</script>
