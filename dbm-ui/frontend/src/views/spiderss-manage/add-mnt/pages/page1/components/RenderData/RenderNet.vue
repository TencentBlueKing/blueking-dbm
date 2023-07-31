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
  <div class="render-net-box">
    <BkLoading :loading="isLoading">
      <TableEditSelect
        ref="editRef"
        v-model="localValue"
        :list="bkNetList"
        :placeholder="t('请输入选择从库')"
        :rules="rules" />
    </BkLoading>
  </div>
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

  import TableEditSelect from '@views/mysql/common/edit/Select.vue';

  import { random } from '@utils';

  import type { IDataRow } from './Row.vue';

  interface Props {
    clusterData: IDataRow['clusterData']
  }

  interface Exposes {
    getValue: (field: string) => Promise<string>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const editRef = ref();
  const localValue = ref<number>(0);
  const bkNetList = shallowRef([] as Array<{ id: number, name: string}>);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('云区域不能为空'),
    },
  ];

  const {
    loading: isLoading,
  } = useRequest(getCloudList, {
    initialData: [],
    onSuccess(data) {
      bkNetList.value = data.map(item => ({
        id: item.bk_cloud_id,
        name: item.bk_cloud_name,
      }));
    },
  });

  watch(() => props.clusterData, () => {
    if (props.clusterData) {
      localValue.value = props.clusterData.cloudId;
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
