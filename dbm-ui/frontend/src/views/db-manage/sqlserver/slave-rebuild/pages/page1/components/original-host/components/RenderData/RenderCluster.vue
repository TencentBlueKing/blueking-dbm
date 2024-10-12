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
      :model-value="localInstanceData?.master_domain"
      :placeholder="t('根据实例生成')"
      readonly />
  </BkLoading>
</template>
<script setup lang="ts">
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkInstance } from '@services/source/dbbase';

  import TableEditInput from '@views/db-manage/tendb-cluster/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    slave?: IDataRow['slave'];
  }

  interface Exposes {
    getValue: () => Promise<{ cluster_ids: number }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const editInputRef = ref();
  const localInstanceData = shallowRef<ServiceReturnType<typeof checkInstance>[number]>();

  const { loading: isLoading, run: fetchCheckInstances } = useRequest(checkInstance, {
    manual: true,
    onSuccess(data) {
      [localInstanceData.value] = data.filter((item) => item.role === 'slave');
    },
  });

  watch(
    () => props.slave,
    () => {
      if (!props.slave) {
        localInstanceData.value = undefined;
        return;
      }
      fetchCheckInstances({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        instance_addresses: [props.slave.instanceAddress],
      });
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return editInputRef.value.getValue().then(() => {
        if (!localInstanceData.value) {
          return Promise.reject();
        }
        return {
          cluster_id: localInstanceData.value.cluster_id,
        };
      });
    },
  });
</script>
