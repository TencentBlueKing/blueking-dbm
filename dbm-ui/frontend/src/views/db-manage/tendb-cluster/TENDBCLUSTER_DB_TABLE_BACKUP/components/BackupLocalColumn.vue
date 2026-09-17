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
  <EditableColumn
    :disabled-method="disabledMethod"
    field="backup_local"
    :label="t('备份位置')"
    :loading="loading"
    :min-width="200"
    required>
    <template #headAppend>
      <BatchEditColumn
        v-model="isShowBatchEdit"
        :data-list="baseList"
        :title="t('备份位置')"
        @change="handleBatchEdit">
        <span
          v-bk-tooltips="t('统一设置：将该列统一设置为相同的值')"
          class="batch-edit-btn"
          @click="handleShowBatchEdit">
          <DbIcon type="bulk-edit" />
        </span>
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :list="backupList" />
  </EditableColumn>
</template>

<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbClusterList } from '@services/source/tendbcluster';

  import { ipPort } from '@common/regex';

  import BatchEditColumn from '@views/db-manage/common/batch-edit-column/Index.vue';

  interface Props {
    cluster: TendbclusterModel;
  }

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const isShowBatchEdit = ref(false);

  const baseList = [
    {
      label: 'RemoteDR',
      value: 'remote',
    },
  ];

  const backupList = shallowRef<Record<'value' | 'label', string>[]>([]);

  const { loading, run: fetchData } = useRequest(getTendbClusterList, {
    manual: true,
    onSuccess(data) {
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
    () => props.cluster,
    () => {
      if (props.cluster.id) {
        fetchData({
          cluster_ids: `${props.cluster.id}`,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const selectValueMap: Record<string, string> = {
    RemoteDB: 'master',
    RemoteDR: 'remote',
    // 兼容旧单据回填：历史值 slave 即 RemoteDR
    slave: 'remote',
  };

  watch(backupList, () => {
    if (!modelValue.value) {
      return;
    }
    const isContains = (value: string) => backupList.value.some((item) => item.value === value);
    // 已是合法选项值（remote / spider_mnt::ip:port），无需转换
    if (isContains(modelValue.value)) {
      return;
    }
    if (ipPort.test(modelValue.value)) {
      // 批量录入的 ip:port 转换为运维节点选项值
      const value = `spider_mnt::${modelValue.value}`;
      modelValue.value = isContains(value) ? value : '';
      return;
    }
    // 批量录入的选项文案（RemoteDB / RemoteDR）转换为对应选项值
    const value = selectValueMap[modelValue.value];
    modelValue.value = value && isContains(value) ? value : '';
  });

  const disabledMethod = (rowData?: any) => {
    if (!rowData.cluster.id) {
      return t('请先选择集群');
    }
    return '';
  };

  const handleShowBatchEdit = () => {
    isShowBatchEdit.value = true;
  };

  const handleBatchEdit = (value: string) => {
    emits('batch-edit', value, 'backup_local');
  };
</script>

<style lang="less" scoped>
  .batch-edit-btn {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
