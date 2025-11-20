<template>
  <EditableTable :model="[]">
    <EditableRow>
      <DbNameColumn
        v-model="localDBName"
        field="db_list"
        :label="t('回档 DB')"
        :show-batch-edit="false"
        @change="handleDbNameChange" />
      <DbNameColumn
        v-model="localDbIgnoreName"
        field="ignore_db_list"
        :label="t('忽略 DB')"
        :required="false"
        :show-batch-edit="false"
        @change="handleDbIgnoreNameChange" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  import DbNameColumn from '@views/db-manage/sqlserver/common/toolbox-field/db-name-column/Index.vue';

  import type { IValue } from '../Index.vue';

  interface Props {
    clusterId: number;
    dbIgnoreName: string[];
    dbName: string[];
  }

  type Emits = (
    e: 'change',
    value: {
      dbIgnoreName: Props['dbIgnoreName'];
      dbName: Props['dbName'];
      renameInfoList: IValue[];
    },
  ) => void;

  interface Expose {
    refresh(): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localDBName = ref(props.dbName);
  const localDbIgnoreName = ref(props.dbIgnoreName);

  watch(
    () => [props.dbName, props.dbIgnoreName],
    () => {
      localDBName.value = [...props.dbName];
      localDbIgnoreName.value = [...props.dbIgnoreName];
    },
    {
      immediate: true,
    },
  );

  const { run: fetchSqlserverDbs } = useRequest(getSqlserverDbs, {
    manual: true,
    onSuccess(data) {
      const renameInfoList = data.map((item) => ({
        db_name: item,
        rename_db_name: '',
        target_db_name: item,
      }));
      emits('change', {
        dbIgnoreName: localDbIgnoreName.value,
        dbName: localDBName.value,
        renameInfoList,
      });
    },
  });

  const handleRefresh = () => {
    if (localDbIgnoreName.value === props.dbName && localDbIgnoreName.value === props.dbIgnoreName) {
      return;
    }
    if (!localDbIgnoreName.value) {
      emits('change', {
        dbIgnoreName: localDbIgnoreName.value,
        dbName: localDBName.value,
        renameInfoList: [],
      });
      return;
    }
    fetchSqlserverDbs({
      cluster_id: props.clusterId,
      db_list: localDBName.value,
      ignore_db_list: localDbIgnoreName.value,
    });
  };

  const handleDbNameChange = (value: string[]) => {
    localDBName.value = value;
    handleRefresh();
  };

  const handleDbIgnoreNameChange = (value: string[]) => {
    localDbIgnoreName.value = value;
    handleRefresh();
  };

  defineExpose<Expose>({
    refresh() {
      handleRefresh();
    },
  });
</script>
