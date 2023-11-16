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
    :data="localValue"
    :is-loading="isLoading"
    :placeholder="t('输入集群后自动生成')" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getCloudList } from '@services/source/ipchooser';

  import RenderText from '@components/tools-table-common/RenderText.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    source?: IDataRow['source']
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const {
    loading: isLoading,
    data: bkNetList,
  } = useRequest(getCloudList);

  const localValue = computed(() => {
    if (!bkNetList.value || bkNetList.value.length < 1 || !props.source) {
      return '';
    }

    const { source } = props;
    const netData = _.find(bkNetList.value, item => item.bk_cloud_id === source.bk_cloud_id);

    return netData ? netData.bk_cloud_name : '--';
  });

</script>
