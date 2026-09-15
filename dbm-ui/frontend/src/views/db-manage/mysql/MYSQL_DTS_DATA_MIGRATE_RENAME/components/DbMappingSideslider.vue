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
 * the specific governing permissions and limitations under the License.
-->

<template>
  <BkSideslider
    :is-show="isShow"
    render-directive="if"
    :width="960"
    @closed="handleClose">
    <template #header>
      <div class="db-mapping-sideslider-header">
        <span>{{ t('库映射') }}</span>
        <span class="header-divider" />
        <span class="header-domains">{{ sourceDomain }} → {{ targetDomain }}</span>
      </div>
    </template>
    <div class="db-mapping-sideslider">
      <BatchInput
        class="mb-16"
        :config="batchInputConfig"
        @change="handleBatchInput" />
      <EditableTable
        ref="mappingTableRef"
        :model="mappingData">
        <EditableRow
          v-for="(item, index) in mappingData"
          :key="index">
          <EditableColumn
            :append-rules="sourceDbRules(index)"
            field="source_db"
            :label="t('源库')"
            :loading="isDbListLoading"
            :min-width="200"
            required>
            <EditableSelect
              v-model="item.source_db"
              filterable
              :placeholder="t('请选择源库')">
              <BkOption
                v-for="db in dbList"
                :key="db"
                :label="db"
                :value="db" />
            </EditableSelect>
          </EditableColumn>
          <EditableColumn
            :append-rules="targetDbRules(index)"
            field="target_db"
            :label="t('目标库')"
            :min-width="200"
            required>
            <EditableInput
              v-model="item.target_db"
              :placeholder="t('请输入目标库名')" />
          </EditableColumn>
          <OperationColumn
            v-model:table-data="mappingData"
            :create-row-method="createMappingRow" />
        </EditableRow>
      </EditableTable>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterDatabaseNameList } from '@services/source/remoteService';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import OperationColumn from '@views/db-manage/common/toolbox-field/column/operation-column/Index.vue';

  interface DbMapping {
    source_db: string;
    target_db: string;
  }

  const props = defineProps<{
    data: DbMapping[];
    isShow: boolean;
    sourceCluster: {
      id: number;
      master_domain: string;
    };
    targetDomain: string;
  }>();

  const emits = defineEmits<{
    (e: 'update:isShow', value: boolean): void;
    (e: 'confirm', value: DbMapping[]): void;
  }>();

  const { t } = useI18n();

  const mappingTableRef = useTemplateRef('mappingTableRef');

  const mappingData = reactive<DbMapping[]>([]);
  const dbList = ref<string[]>([]);

  const sourceDomain = computed(() => props.sourceCluster.master_domain);

  const batchInputConfig = [
    {
      case: 'order_db',
      key: 'source_db',
      label: t('源库'),
    },
    {
      case: 'order_archive',
      key: 'target_db',
      label: t('目标库'),
    },
  ];

  const createMappingRow = () => ({
    source_db: '',
    target_db: '',
  });

  const sourceDbRules = (currentIndex: number) => [
    {
      message: t('源库不可重复'),
      trigger: 'change',
      validator: (value: string) =>
        !value || mappingData.filter((_, i) => i !== currentIndex).every((item) => item.source_db !== value),
    },
  ];

  const targetDbRules = (currentIndex: number) => [
    {
      message: t('目标库不可重复'),
      trigger: 'change',
      validator: (value: string) =>
        !value || mappingData.filter((_, i) => i !== currentIndex).every((item) => item.target_db !== value),
    },
  ];

  const { loading: isDbListLoading, run: fetchDbList } = useRequest(getClusterDatabaseNameList, {
    manual: true,
    onSuccess(data) {
      const [current] = data;
      dbList.value = current?.databases || [];
    },
  });

  watch(
    () => props.isShow,
    (show) => {
      if (show) {
        mappingData.splice(
          0,
          mappingData.length,
          ...(props.data.length ? _.cloneDeep(props.data) : [createMappingRow()]),
        );
        dbList.value = [];
        if (props.sourceCluster.id) {
          fetchDbList({ cluster_ids: [props.sourceCluster.id] });
        }
      }
    },
  );

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.map((item) => ({
      source_db: item.source_db || '',
      target_db: item.target_db || '',
    }));
    if (isClear) {
      mappingData.splice(0, mappingData.length, ...dataList);
    } else {
      const validRows = mappingData.filter((item) => item.source_db || item.target_db);
      mappingData.splice(0, mappingData.length, ...validRows, ...dataList);
    }
    setTimeout(() => {
      mappingTableRef.value?.validate();
    }, 200);
  };

  const handleConfirm = async () => {
    const result = await mappingTableRef.value?.validate();
    if (!result) {
      return;
    }
    emits('confirm', _.cloneDeep(mappingData));
    emits('update:isShow', false);
  };

  const handleClose = () => {
    emits('update:isShow', false);
  };
</script>
<style lang="less" scoped>
  .db-mapping-sideslider-header {
    display: flex;
    align-items: center;

    .header-divider {
      width: 1px;
      height: 14px;
      margin: 0 12px;
      background-color: #dcdee5;
    }

    .header-domains {
      font-size: 12px;
      color: #979ba5;
    }
  }

  .db-mapping-sideslider {
    padding: 20px 24px;
  }
</style>
