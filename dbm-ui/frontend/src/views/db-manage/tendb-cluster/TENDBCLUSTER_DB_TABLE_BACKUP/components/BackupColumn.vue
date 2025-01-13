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
    field="backup"
    :label="t('备份位置')"
    :loading="loading"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="showBatchEdit"
        :data-list="backupList"
        :title="t('备份位置')"
        type="select"
        @change="handleBatchEditChange">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleBatchEditShow">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <Select
      v-model="modelValue"
      :list="backupList" />
  </Column>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getTendbClusterList } from '@services/source/tendbcluster';

  import { Column, Select } from '@components/editable-table/Index.vue';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    cluster: {
      id: number;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const showBatchEdit = ref(false);
  const backupList = shallowRef<Record<'value' | 'label', string>[]>([]);

  const { run: fetchClusterList, loading } = useRequest(getTendbClusterList, {
    manual: true,
    onSuccess(data) {
      const baseList = [
        {
          value: 'remote',
          label: 'RemoteDR',
        },
      ];
      if (data.results.length < 1) {
        backupList.value = [...baseList];
        return;
      }
      const mntList = data.results[0].spider_mnt.map((item) => ({
        label: `${item.ip}:${item.port}`,
        value: `spider_mnt::${item.instance}`,
      }));
      backupList.value = [...baseList, ...mntList];
    },
  });

  watch(
    () => props.cluster.id,
    () => {
      if (props.cluster.id) {
        fetchClusterList({
          cluster_ids: [props.cluster.id],
        });
      }
    },
  );

  const handleBatchEditShow = () => {
    showBatchEdit.value = true;
  };

  const handleBatchEditChange = (value: string) => {
    modelValue.value = value;
  };
</script>
<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
