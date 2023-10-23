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
      ref="inputRef"
      :model-value="relatedClusterList.map(item => item.cluster_name).join(',')"
      :placeholder="t('输入主库后自动生成')"
      readonly
      :rules="rules" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  // TODO INTERFACE
  import { checkMysqlInstances } from '@services/source/instances';
  import type { InstanceInfos } from '@services/types/clusters';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import type { IHostData } from './Row.vue';

  interface Props {
    masterData?: IHostData
  }

  interface Exposes {
    getValue: () => Promise<Record<'cluster_id', number>>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const inputRef = ref();
  const isLoading = ref(false);
  const relatedClusterList = shallowRef<InstanceInfos['related_clusters']>([]);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
  ];

  watch(() => props.masterData, () => {
    relatedClusterList.value = [];
    if (props.masterData && props.masterData.ip) {
      isLoading.value = true;
      checkMysqlInstances({
        bizId: currentBizId,
        instance_addresses: [props.masterData.ip],
      }).then((data) => {
        if (data.length < 1) {
          return;
        }

        const [currentProxyData] = data;
        relatedClusterList.value = currentProxyData.related_clusters;
      })
        .finally(() => {
          isLoading.value = false;
        });
    }
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return inputRef.value
        .getValue()
        .then(() => ({
          cluster_id: relatedClusterList.value.map(item => item.id)[0],
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-cluster-box {
    padding: 10px 16px;
    line-height: 20px;
  }
</style>
