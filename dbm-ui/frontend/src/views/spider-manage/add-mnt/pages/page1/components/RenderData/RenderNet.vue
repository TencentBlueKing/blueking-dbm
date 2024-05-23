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
    ref="editRef"
    :data="localValue"
    :is-loading="isLoading || isClusterDataLoading"
    :placeholder="t('请先输入集群')"
    :rules="rules" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref, shallowRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type SpiderModel from '@services/model/spider/spider';
  import { getCloudList } from '@services/source/ipchooser';
  import { getSpiderDetail } from '@services/source/spider';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  interface Props {
    clusterId: number;
  }

  interface Emits {
    (e: 'clusterChange', value: SpiderModel): void;
  }

  interface Exposes {
    getValue: (field: string) => Promise<string>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const editRef = ref();
  const bkNetList = shallowRef<{ bk_cloud_id: number; bk_cloud_name: string }[]>([]);
  const localBkNetId = ref<number>();

  const localValue = computed(() => {
    const target = _.find(bkNetList.value, (item) => item.bk_cloud_id === localBkNetId.value);
    if (target) {
      return target.bk_cloud_name;
    }
    return '';
  });

  const rules = [
    {
      validator: () => Number(localBkNetId.value) > -1,
      message: t('管控区域不能为空'),
    },
  ];

  const { loading: isLoading } = useRequest(getCloudList, {
    initialData: [],
    onSuccess(data) {
      bkNetList.value = data;
    },
  });

  const { loading: isClusterDataLoading, run: fetchClusetrData } = useRequest(getSpiderDetail, {
    manual: true,
    onSuccess(data) {
      localBkNetId.value = data.bk_cloud_id;
      emits('clusterChange', data);
    },
  });

  watch(
    () => props.clusterId,
    () => {
      if (props.clusterId) {
        fetchClusetrData({
          id: props.clusterId,
        });
      }
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      return editRef.value.getValue().then(() => ({
        bk_cloud_id: localBkNetId.value,
      }));
    },
  });
</script>
