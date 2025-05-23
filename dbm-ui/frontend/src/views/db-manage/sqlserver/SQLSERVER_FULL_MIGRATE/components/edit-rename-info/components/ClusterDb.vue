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
        check-not-exist
        :cluster-id="data.srcCluster.id"
        field="dbName"
        :label="t('迁移 DB 名')"
        required
        :show-batch-edit="false" />
      <DbNameColumn
        v-model="item.dbIgnoreName"
        check-not-exist
        :cluster-id="data.srcCluster.id"
        field="dbIgnoreName"
        :label="t('忽略 DB 名')"
        :required="false"
        :show-batch-edit="false" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';

  import { type IValue } from '../Index.vue';

  interface Props {
    data: {
      dstCluster: { id: number; master_domain: string }[];
      srcCluster: { id: number; master_domain: string };
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

  onMounted(fetchData);
</script>
