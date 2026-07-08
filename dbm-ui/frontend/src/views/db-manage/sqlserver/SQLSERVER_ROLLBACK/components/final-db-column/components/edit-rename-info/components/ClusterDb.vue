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
  <EditableTable
    class="mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <DbNameColumn
        v-model="item.dbName"
        allow-asterisk
        :cluster-id="data.srcCluster.id"
        field="dbName"
        :label="t('回档 DB')"
        required
        :show-batch-edit="false" />
      <DbNameColumn
        v-model="item.dbIgnoreName"
        :cluster-id="data.srcCluster.id"
        field="dbIgnoreName"
        :label="t('忽略 DB')"
        :required="false"
        :show-batch-edit="false" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';

  import { type IValue } from '../Index.vue';

  interface Props {
    data: {
      backupDbList?: string[];
      srcCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    dbIgnoreName: string[];
    dbName: string[];
    renameInfoList: IValue[];
  }>({
    required: true,
  });

  const { t } = useI18n();

  const tableData = computed(() => [modelValue.value]);

  const getFilteredDbList = () => {
    if (!props.data.backupDbList?.length) {
      return [];
    }

    const dbPatterns = tableData.value[0].dbName;
    const ignores = tableData.value[0].dbIgnoreName;

    // 匹配 dbPattern 的库（支持 * 和 % 通配符）
    const matched = props.data.backupDbList.filter((db) => {
      // 先检查是否匹配 ignore 模式
      const isIgnored = ignores.some((ignore) => {
        if (ignore === '*') return true;
        const regex = new RegExp(`^${ignore.replace(/%/g, '.*').replace(/\*/g, '.*')}$`, 'i');
        return regex.test(db);
      });
      if (isIgnored) return false;

      // 检查是否匹配 db_pattern
      return dbPatterns.some((pattern) => {
        if (pattern === '*') return true;
        const regex = new RegExp(`^${pattern.replace(/%/g, '.*').replace(/\*/g, '.*')}$`, 'i');
        return regex.test(db);
      });
    });

    return matched;
  };

  const fetchData = () => {
    if (!props.data.srcCluster.id || modelValue.value.dbName.length < 1) {
      return;
    }

    const dbs = getFilteredDbList();

    const existingMap = new Map(modelValue.value.renameInfoList.map((item) => [item.db_name, item]));

    modelValue.value.renameInfoList = dbs.map((item) => {
      const existing = existingMap.get(item);
      if (existing) {
        return existing;
      }
      return {
        db_name: item,
        rename_db_name: '',
        target_db_name: item,
      };
    });
  };

  watch(() => [tableData.value[0].dbName, tableData.value[0].dbIgnoreName], fetchData);
</script>
