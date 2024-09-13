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
    ref="editSelectRef"
    :data="localValue"
    :is-loading="isLoading"
    :placeholder="t('输入集群后自动生成')" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getHostTopoInfos } from '@services/source/ipchooser';

  import { useGlobalBizs } from '@stores';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    source?: IDataRow['source'];
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const editSelectRef = ref();
  const localValue = ref('');

  const { loading: isLoading, run: fetchHostTopoInfo } = useRequest(getHostTopoInfos, {
    manual: true,
    onSuccess(data) {
      if (data.hosts_topo_info.length > 0) {
        [localValue.value] = data.hosts_topo_info[0].topo;
      } else {
        localValue.value = '--';
      }
    },
  });

  watch(
    () => props.source,
    () => {
      if (!props.source) {
        localValue.value = '';
        return;
      }
      fetchHostTopoInfo({
        bk_biz_id: currentBizId,
        filter_conditions: {
          bk_host_innerip: [`${props.source.bk_cloud_id}:${props.source.ip}`],
        },
      });
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return editSelectRef.value.getValue().then(() => ({
        module: localValue.value,
      }));
    },
  });
</script>
