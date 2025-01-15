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
  <Column
    field="module"
    :label="t('模块')"
    :loading="loading"
    :min-width="150"
    required>
    <Block
      v-model="modelValue"
      :placeholder="t('自动生成')" />
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getHostTopoInfos } from '@services/source/ipchooser';

  import { Block, Column } from '@components/editable-table/Index.vue';

  interface Props {
    source: {
      bk_host_innerip: string;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const { run: queryHostModule, loading } = useRequest(getHostTopoInfos, {
    manual: true,
    onSuccess: (data) => {
      if (data.hosts_topo_info.length > 0) {
        [modelValue.value] = data.hosts_topo_info[0].topo;
      }
    },
  });

  watch(
    () => props.source,
    () => {
      if (props.source.bk_host_innerip) {
        queryHostModule({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          filter_conditions: {
            bk_host_innerip: [props.source.bk_host_innerip],
          },
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
