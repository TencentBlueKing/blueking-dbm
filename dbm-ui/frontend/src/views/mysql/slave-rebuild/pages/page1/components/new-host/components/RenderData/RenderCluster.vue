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
  <BkLoading :loading="isLoading">
    <TableEditInput
      ref="editInputRef"
      :model-value="renderText"
      :placeholder="t('根据实例生成')"
      readonly />
  </BkLoading>
</template>
<script setup lang="ts">
  import {
    computed,
    shallowRef  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkMysqlInstances } from '@services/source/instances';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    oldSlave?: IDataRow['oldSlave']
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const editInputRef = ref();
  const localRelateClusterList = shallowRef<ServiceReturnType<typeof checkMysqlInstances>[0]['related_clusters']>([]);

  const renderText = computed(() => {
    if (localRelateClusterList.value?.length < 1) {
      return '';
    }
    return localRelateClusterList.value.map(item => item.master_domain).join('\n');
  });

  const {
    loading: isLoading,
    run: fetchCheckMysqlInstances,
  } = useRequest(checkMysqlInstances, {
    manual: true,
    onSuccess(data) {
      const [instanceData] = data;
      localRelateClusterList.value = instanceData.related_clusters;
    },
  });

  watch(() => props.oldSlave, () => {
    if (!props.oldSlave) {
      localRelateClusterList.value = [];
      return;
    }
    fetchCheckMysqlInstances({
      bizId: currentBizId,
      instance_addresses: [props.oldSlave.ip],
    });
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return editInputRef.value.getValue()
        .then(() => {
          if (localRelateClusterList.value.length < 1) {
            return Promise.reject();
          }
          return {
            cluster_ids: localRelateClusterList.value.map(item => item.id),
          };
        });
    },
  });
</script>
