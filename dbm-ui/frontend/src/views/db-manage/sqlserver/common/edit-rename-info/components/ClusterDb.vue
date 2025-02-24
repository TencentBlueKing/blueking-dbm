<template>
  <BkTable
    :border="['outer', 'row', 'col']"
    :data="[{}]">
    <BkTableColumn :label="t('回档 DB')">
      <RenderDbName
        :model-value="localDBName"
        required
        @change="handleDbNameChange" />
    </BkTableColumn>
    <BkTableColumn :label="t('忽略 DB')">
      <RenderDbName
        :model-value="localDbIgnoreName"
        :required="false"
        @change="handleDnIgnoreNameChange" />
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="tsx">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSqlserverDbs } from '@services/source/sqlserver';

  import RenderDbName from '@views/db-manage/sqlserver/common/DbName.vue';

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

  const handleDnIgnoreNameChange = (value: string[]) => {
    localDbIgnoreName.value = value;
    handleRefresh();
  };

  defineExpose<Expose>({
    refresh() {
      handleRefresh();
    },
  });
</script>
