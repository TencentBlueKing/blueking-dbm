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
  <BkLoading :loading="isListLoading">
    <TableEditSelect
      ref="editSelectRef"
      :list="backupList"
      :model-value="modelValue"
      :placeholder="$t('请选择')"
      :rules="rules"
      @change="(value) => handleChange(value as string)" />
  </BkLoading>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getList } from '@services/spider';

  import TableEditSelect from '@views/mysql/common/edit/Select.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    clusterData: IDataRow['clusterData'],
    modelValue: string
  }

  interface Exposes {
    getValue: () => Promise<Record<string, string>>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('备份源不能为空'),
    },
  ];

  const editSelectRef = ref();
  const localValue = ref('');
  const backupList = shallowRef<Record<'name'|'id', string>[]>([]);

  const {
    run: fetchClusterList,
    loading: isListLoading,
  } = useRequest(getList, {
    onSuccess(data) {
      if (data.results.length < 1) {
        return;
      }
      const mntList = data.results[0].spider_mnt.map(item => ({
        name: `运维节点(${item.ip}#${item.port})`,
        id: item.instance,
      }));
      backupList.value = [
        {
          id: 'remote',
          name: 'remote',
        },
        ...mntList,
      ];
    },
    manual: true,
  });

  watch(() => props.modelValue, () => {
    localValue.value = props.modelValue;
  }, {
    immediate: true,
  });

  watch(() => props.clusterData, () => {
    if (props.clusterData) {
      fetchClusterList({
        cluster_ids: props.clusterData.id,
      });
    }
  }, {
    immediate: true,
  });

  const handleChange = (value: string) => {
    localValue.value = value;
  };

  defineExpose<Exposes>({
    getValue() {
      return editSelectRef.value.getValue()
        .then(() => ({
          backup_local: localValue.value,
        }));
    },
  });
</script>
