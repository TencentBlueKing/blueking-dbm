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
        :show-batch-edit="false"
        check-not-exist
        :cluster-id="data.srcCluster.id"
        field="dbName"
        :label="t('迁移 DB 名')"
        required />
      <DbNameColumn
        v-model="item.dbIgnoreName"
        :show-batch-edit="false"
        check-not-exist
        :required="false"
        :cluster-id="data.srcCluster.id"
        field="dbIgnoreName"
        :label="t('忽略 DB 名')" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';

  import type { IValue } from '../Index.vue';

  interface Props {
    data: {
      dstCluster: { id: number; master_domain: string }[];
      srcCluster: { id: number; master_domain: string };
    };
  }

  interface Exposes {
    fetchData(): Promise<void>;
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
  };

  watch(() => [tableData.value[0].dbName, tableData.value[0].dbIgnoreName], fetchData);

  defineExpose<Exposes>({
    fetchData,
  });
</script>
