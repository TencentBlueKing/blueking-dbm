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
    <TableEditSelect
      ref="inputRef"
      disabled
      :list="list"
      :placeholder="t('请选择')"
      textarea />
  </BkLoading>
</template>
<script setup lang="ts">
  import {
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SpiderModel from '@services/model/spider/spider';
  import { getDetail } from '@services/spider';

  import TableEditSelect from '@views/mysql/common/edit/Select.vue';

  interface Props {
    clusterId: number
  }
  interface Exposes {
    getValue: () => Promise<{
      slaves: {
        id: number,
        ip: string,
        port: number,
        instance_inner_role: 'master'
      }[]
    }>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const wholeSlaveList = shallowRef<SpiderModel['spider_slave']>([]);
  const list = shallowRef<{id: number, name: string}[]>([]);

  const {
    loading: isLoading,
    run: fetchClusetrData,
  } = useRequest(getDetail, {
    manual: true,
    onSuccess(data) {
      wholeSlaveList.value = data.spider_slave;
      list.value = data.spider_slave.map(item => ({
        id: item.bk_instance_id,
        name: item.instance,
      }));
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
      return Promise.resolve({
        slaves: [],
      });
    },
  });
</script>
