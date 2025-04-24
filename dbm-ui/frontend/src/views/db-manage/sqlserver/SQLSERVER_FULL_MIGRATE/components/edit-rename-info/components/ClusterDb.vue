<template>
  <EditableTable
    ref="table"
    class="mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <TagDbNameColumn
        v-model="item.dbName"
        allow-asterisk
        :batch-edit="false"
        check-not-exist
        :cluster-id="data.srcCluster.id"
        field="dbName"
        :label="t('迁移 DB 名')"
        required />
      <TagDbNameColumn
        v-model="item.dbIgnoreName"
        :batch-edit="false"
        check-not-exist
        :cluster-id="data.srcCluster.id"
        field="dbIgnoreName"
        :label="t('忽略 DB 名')" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  import TagDbNameColumn from '@views/db-manage/sqlserver/common/tag-db-name-column/Index.vue';

  import type { IValue } from '../Index.vue';

  interface Props {
    data: {
      dstCluster: { id: number; master_domain: string }[];
      srcCluster: { id: number; master_domain: string };
    };
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    fetchData(): void;
    validate(): Promise<boolean>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    dbIgnoreName: string[];
    dbName: string[];
    renameInfoList: IValue[];
  }>({
    required: true,
  });

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const tableData = computed(() => [modelValue.value]);

  const fetchData = async () => {
    if (!props.data.srcCluster.id || modelValue.value.dbName.length < 1) {
      return;
    }

    const dbs = await getSqlserverDbs({
      cluster_id: props.data.srcCluster.id,
      db_list: tableData.value[0].dbName,
      ignore_db_list: tableData.value[0].dbIgnoreName,
    });

    modelValue.value.renameInfoList = dbs.map((item) => ({
      db_name: item,
      rename_cluster_list: [],
      rename_db_name: '',
      target_db_name: item,
    }));

    emits('change');
  };

  watch(() => [tableData.value[0].dbName, tableData.value[0].dbIgnoreName], fetchData);

  defineExpose<Exposes>({
    fetchData,
    validate() {
      return tableRef.value?.validate()?.then((res) => res) ?? Promise.resolve(false);
    },
  });
</script>
