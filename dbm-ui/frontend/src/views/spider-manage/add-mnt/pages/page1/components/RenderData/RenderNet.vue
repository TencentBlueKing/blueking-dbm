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
  <!-- <BkLoading :loading="isLoading || isClusterDataLoading"> -->
  <TableEditSelect
    ref="editRef"
    v-model="localValue"
    :disabled="!clusterId"
    :list="bkNetList"
    :placeholder="t('请先输入集群')"
    :rules="rules" />
  <!-- </BkLoading> -->
</template>
<script setup lang="ts">
  import {
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getCloudList } from '@services/ip';
  import type SpiderModel from '@services/model/spider/spider';
  import { getDetail } from '@services/spider';

  import TableEditSelect from '@views/redis/common/edit/Select.vue';

  interface Props {
    clusterId: number
  }

  interface Emits {
    (e: 'clusterChange', value: SpiderModel): void
  }

  interface Exposes {
    getValue: (field: string) => Promise<string>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const editRef = ref();
  const localValue = ref<number>();
  const bkNetList = shallowRef([] as Array<{ value: number, label: string}>);
  const localClusterData = ref<SpiderModel>();

  const rules = [
    {
      validator: (value: number) => value > -1,
      message: t('云区域不能为空'),
    },
  ];

  const {
    loading: isLoading,
  } = useRequest(getCloudList, {
    initialData: [],
    onSuccess(data) {
      bkNetList.value = data.map(item => ({
        value: item.bk_cloud_id,
        label: item.bk_cloud_name,
      }));
    },
  });

  const {
    loading: isClusterDataLoading,
    run: fetchClusetrData,
  } = useRequest(getDetail, {
    manual: true,
    onSuccess(data) {
      localValue.value = data.bk_cloud_id;
      localClusterData.value = data;
      emits('clusterChange', data);
    },
  });

  watch(() => props.clusterId, () => {
    if (props.clusterId) {
      fetchClusetrData({
        id: props.clusterId,
      });
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => ({
          bk_cloud_id: localValue.value,
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-net-box {
    position: relative;
  }
</style>
