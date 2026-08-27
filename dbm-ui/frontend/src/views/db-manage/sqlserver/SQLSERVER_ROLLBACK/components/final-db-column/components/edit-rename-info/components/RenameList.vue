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
    ref="table"
    class="mb-20"
    :model="modelValue.renameInfoList">
    <EditableRow
      v-for="(item, index) in modelValue.renameInfoList"
      :key="index">
      <EditableColumn
        field="db_name"
        :label="t('源库名')"
        required>
        <EditableBlock v-model="item.db_name" />
      </EditableColumn>
      <EditableColumn
        :append-rules="targetDbNameRules"
        field="target_db_name"
        :label="t('恢复后库名')"
        required>
        <EditableInput
          v-model="item.target_db_name"
          :class="{
            'is-change': valueMemo[index]?.target_db_name && valueMemo[index].db_name !== item.target_db_name,
          }" />
      </EditableColumn>
      <EditableColumn
        :append-rules="renameDbNameRules"
        field="rename_db_name"
        :label="t('已有库新名')">
        <EditableInput
          v-model="item.rename_db_name"
          :class="{
            'is-change': valueMemo[index]?.rename_db_name && valueMemo[index].target_db_name !== item.rename_db_name,
          }"
          @change="() => handleChange(index)" />
      </EditableColumn>
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { checkClusterDatabase } from '@services/source/dbbase';

  import { type IValue } from '../Index.vue';

  interface Props {
    data: {
      targetCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  interface Exposes {
    validate(): Promise<boolean>;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<{
    renameInfoList: IValue[];
  }>({
    required: true,
  });

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const valueMemo = _.cloneDeep(modelValue.value.renameInfoList);

  const targetDbNameRules = [
    {
      message: t('跟已存在的 DB 名冲突，请修改其一'),
      trigger: 'blur',
      validator: (
        value: string,
        {
          rowData,
        }: {
          rowData: IValue;
        },
      ) => {
        // rename_db_name(第三列)可用时，不需要校验 target_db_name(第二列)
        if (rowData.rename_db_name) {
          return true;
        }
        if (!value) {
          return true;
        }
        return (
          Number(
            _.countBy(
              modelValue.value.renameInfoList.filter((item) => !item.rename_db_name),
              'target_db_name',
            )[value],
          ) < 2
        );
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (
        value: string,
        {
          rowData,
        }: {
          rowData: IValue;
        },
      ) => {
        // rename_db_name(第三列)可用时，不需要校验 target_db_name(第二列)
        if (rowData.rename_db_name) {
          return true;
        }
        if (!value) {
          return true;
        }
        return checkClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.data.targetCluster.id,
          db_list: [value],
        }).then((data) => {
          if (data[value]) {
            return t('集群x已存在DB名y', {
              x: props.data.targetCluster.master_domain,
              y: value,
            });
          }
          return true;
        });
      },
    },
  ];

  const renameDbNameRules = [
    {
      message: t('和其它已填写数据重复'),
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const targetDbCount =
          Number(
            _.countBy(
              modelValue.value.renameInfoList.filter((item) => !item.rename_db_name),
              'target_db_name',
            )[value],
          ) || 0;
        const count = Number(_.countBy(modelValue.value.renameInfoList, 'rename_db_name')[value]) || 0;
        return targetDbCount + count < 2;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        return checkClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.data.targetCluster.id,
          db_list: [value],
        }).then((data) => {
          if (data[value]) {
            return t('集群x已存在DB名y', {
              x: props.data.targetCluster.master_domain,
              y: value,
            });
          }
          return true;
        });
      },
    },
  ];

  const handleChange = (index: number) => {
    tableRef.value?.validateByRowIndex(index);
  };

  watch(
    () => modelValue.value.renameInfoList,
    () => {
      Object.assign(valueMemo, _.cloneDeep(modelValue.value.renameInfoList));
      tableRef.value?.validateByField('target_db_name');
    },
    {
      deep: true,
    },
  );

  defineExpose<Exposes>({
    validate() {
      return tableRef.value!.validate();
    },
  });
</script>
<style lang="less">
  .is-change {
    background: #fff8e9;

    :deep(.bk-input--text) {
      background: inherit;
    }
  }
</style>
