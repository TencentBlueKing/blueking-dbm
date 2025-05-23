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
        :label="t('迁移 DB 名称')"
        required>
        <EditableBlock v-model="item.db_name" />
      </EditableColumn>
      <EditableColumn
        :append-rules="targetDbNameRules"
        field="target_db_name"
        :label="t('迁移后 DB 名称（自动生成，可修改）')"
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
        :label="t('已存在的 DB（可修改）')">
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

  import { batchCheckClusterDatabase } from '@services/source/dbbase';

  import { type IValue } from '../Index.vue';

  interface Props {
    data: {
      dstCluster: {
        id: number;
        master_domain: string;
      }[];
      srcCluster: {
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

  const dstClusterIds = computed(() => props.data.dstCluster.map((item) => item.id));
  const dstClusterMap = computed(() => Object.fromEntries(props.data.dstCluster.map((cur) => [cur.id, cur])));

  const valueMemo = _.cloneDeep(modelValue.value.renameInfoList);
  const renameClusterIds: Record<string, number[]> = {};

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
        return Number(_.countBy(modelValue.value.renameInfoList, 'target_db_name')[value]) < 2;
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
        return batchCheckClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: dstClusterIds.value,
          db_list: [value],
        }).then((data) => {
          const existDomainList: string[] = [];
          Object.entries(data).forEach(([clusterId, dbCheckMap]) => {
            if (dbCheckMap[value]) {
              existDomainList.push(dstClusterMap.value[clusterId].master_domain);
              if (!renameClusterIds[rowData.db_name]) {
                renameClusterIds[rowData.db_name] = [];
              }
              renameClusterIds[rowData.db_name].push(Number(clusterId));
            }
          });
          if (existDomainList.length) {
            return t('集群x已存在DB名y', {
              x: existDomainList.join('、'),
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
        const targetDbCount = Number(_.countBy(modelValue.value.renameInfoList, 'target_db_name')[value]) || 0;
        const count = Number(_.countBy(modelValue.value.renameInfoList, 'rename_db_name')[value]) || 0;
        return targetDbCount + count < 2;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (
        value: string,
        {
          rowData,
          rowIndex,
        }: {
          rowData: IValue;
          rowIndex: number;
        },
      ) => {
        if (!value) {
          return true;
        }
        return batchCheckClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: dstClusterIds.value,
          db_list: [value],
        }).then((data) => {
          const existDomainList: string[] = [];
          Object.entries(data).forEach(([clusterId, dbCheckMap]) => {
            if (dbCheckMap[value]) {
              existDomainList.push(dstClusterMap.value[clusterId].master_domain);
            }
          });
          if (existDomainList.length) {
            return t('集群x已存在DB名y', {
              x: existDomainList.join('、'),
              y: value,
            });
          }
          // rename_cluster_list依赖于第二列的校验
          modelValue.value.renameInfoList[rowIndex] = Object.assign(rowData, {
            rename_cluster_list: _.uniq(renameClusterIds[rowData.db_name]),
          });
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
      return tableRef.value?.validate()?.then((res) => res) ?? Promise.resolve(false);
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
