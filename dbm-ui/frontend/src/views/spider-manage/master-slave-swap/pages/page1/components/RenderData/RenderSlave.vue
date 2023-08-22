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
      :model-value="slaveHostData?.ip"
      :placeholder="t('选择目标主库后自动生成')"
      readonly
      :rules="rules" />
  </BkLoading>
</template>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getIntersectedSlaveMachinesFromClusters } from '@services/mysqlCluster';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/mysql/common/edit/Input.vue';

  interface Props {
    clusterList: number []
  }

  interface Exposes {
    getValue: (field: string) => Promise<string>
  }

  interface ISlaveHost {
    bk_biz_id: number,
    bk_cloud_id: number,
    bk_host_id: number,
    ip: string,
  }

  const props = defineProps<Props>();


  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const inputRef = ref();
  const isLoading = ref(false);

  const slaveHostData = ref<ISlaveHost>();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('从库主机不能为空'),
    },
  ];

  watch(() => props.clusterList, () => {
    if (props.clusterList.length > 0) {
      isLoading.value = true;
      getIntersectedSlaveMachinesFromClusters({
        bk_biz_id: currentBizId,
        cluster_ids: props.clusterList,
      }).then((data) => {
        [slaveHostData.value] = data;
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
          slave: slaveHostData.value,
        }));
    },
  });
</script>
