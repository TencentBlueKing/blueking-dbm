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
      ref="editSelectRef"
      :model-value="localValue"
      :placeholder="t('输入集群后自动生成')"
      readonly />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  // TODO INTERFACE
  import { getHostTopoInfos } from '@services/ip';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    source: IDataRow['source']
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const editSelectRef = ref();
  const localValue = ref('');

  const {
    loading: isLoading,
    run: fetchHostTopoInfo,
  } = useRequest(getHostTopoInfos, {
    manual: true,
    onSuccess(data) {
      if (data.hosts_topo_info.length > 0) {
        [localValue.value] = data.hosts_topo_info[0].topo;
      }
    },
  });

  watch(() => props.source, () => {
    if (!props.source) {
      localValue.value = '';
      return;
    }
    fetchHostTopoInfo({
      bk_biz_id: currentBizId,
      filter_conditions: {
        bk_host_innerip: [`${props.source.cloud_area.id}:${props.source.ip}`],
      },
    });
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return editSelectRef.value.getValue()
        .then(() => ({
          module: localValue.value,
        }));
    },
  });
</script>
