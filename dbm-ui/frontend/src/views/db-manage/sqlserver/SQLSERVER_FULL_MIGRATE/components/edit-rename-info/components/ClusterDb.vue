<template>
  <EditableTable
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
  import { useRequest } from 'vue-request';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  import TagDbNameColumn from '@views/db-manage/sqlserver/common/tag-db-name-column/Index.vue';

  import type { IValue } from '../Index.vue';

  interface Props {
    data: {
      srcCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  type Emits = (e: 'change') => void;

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

  const tableData = computed(() => [modelValue.value]);

  const { run: fetchSqlserverDbs } = useRequest(getSqlserverDbs, {
    manual: true,
    onSuccess(data) {
      modelValue.value.renameInfoList = data.map((item) => ({
        db_name: item,
        rename_cluster_list: [],
        rename_db_name: '',
        target_db_name: item,
      }));
      emits('change');
    },
  });

  watch(
    () => [tableData.value[0].dbName, tableData.value[0].dbIgnoreName],
    ([dbName, dbIgnoreName]) => {
      if (!props.data.srcCluster.id || dbName.length < 1) {
        return;
      }
      fetchSqlserverDbs({
        cluster_id: props.data.srcCluster.id,
        db_list: dbName,
        ignore_db_list: dbIgnoreName,
      });
    },
  );
</script>
