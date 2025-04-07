<template>
  <EditableColumn
    :disabled-method="disabledMethod"
    field="renameInfoList"
    :label="t('迁移后 DB 名')"
    :loading="loading"
    :min-width="300"
    required
    :rules="rules">
    <EditableBlock
      style="cursor: pointer"
      @click="handleShowEditName">
      <span v-if="noConflictDb && !hasEditRename">--</span>
      <span
        v-else-if="noConflictDb && hasEditRename"
        style="color: #2dcb56">
        {{ t('已更新') }}
      </span>
      <I18nT
        v-else
        keypath="n项待修改">
        <span style="padding-right: 4px; font-weight: bold; color: #ea3636">
          {{ conflictDbList.length }}
        </span>
      </I18nT>
    </EditableBlock>
  </EditableColumn>
  <EditRenameInfo
    ref="editName"
    v-model="localValue"
    v-model:is-show="isShowEditName"
    :conflict-db-list="conflictDbList"
    :data="data"
    @submit="handleSubmit" />
</template>

<script setup lang="ts">
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkClusterDatabase } from '@services/source/dbbase';
  import { getSqlserverDbs } from '@services/source/sqlserver';

  import { makeMap } from '@utils';

  import EditRenameInfo, { type IValue } from './edit-rename-info/Index.vue';

  interface Props {
    data: {
      dstCluster: { id: number; master_domain: string }[];
      srcCluster: { id: number; master_domain: string };
    };
  }

  const props = defineProps<Props>();

  const dbName = defineModel<string[]>('dbName', { required: true });
  const dbIgnoreName = defineModel<string[]>('dbIgnoreName', { required: true });
  const renameInfoList = defineModel<IValue[]>({ required: true });

  const { t } = useI18n();
  const editRenameRef = useTemplateRef('editName');

  const isShowEditName = ref(false);
  const hasEditRename = ref(false);
  const localValue = ref<InstanceType<typeof EditRenameInfo>['modelValue']>({
    dbIgnoreName: [],
    dbName: [],
    renameInfoList: [],
  });
  const conflictDbList = ref<string[]>([]);
  let currentSrcClusterId = 0;

  const noConflictDb = computed(() => conflictDbList.value.length === 0);

  const rules = [
    {
      message: t('构造后 DB 名不能为空'),
      trigger: 'change',
      validator: () => renameInfoList.value.length > 0,
    },
    {
      message: t('构造后 DB 名待有冲突更新'),
      trigger: 'change',
      validator: () => noConflictDb.value,
    },
    {
      message: t('迁移后 DB 和迁移 DB 数量不匹配'),
      trigger: 'change',
      validator: () => {
        const dbIgnoreNameMap = makeMap(dbIgnoreName.value);
        const filteredDbNames = dbName.value.filter(
          (item) => !/\*/.test(item) && !/%/.test(item) && !dbIgnoreNameMap[item],
        );
        return filteredDbNames.length <= renameInfoList.value.length;
      },
    },
  ];

  const { loading, run: runCheckClusterDatabase } = useRequest(checkClusterDatabase, {
    manual: true,
    onSuccess(data) {
      conflictDbList.value = Object.keys(
        Object.values(data).reduce(
          (acc, item) => {
            Object.entries(item).forEach(([db, isExist]) => {
              if (isExist) {
                Object.assign(acc, {
                  [db]: true,
                });
              }
            });
            return acc;
          },
          {} as Record<string, true>,
        ),
      );
    },
  });

  const { run: fetchSqlserverDbs } = useRequest(getSqlserverDbs, {
    manual: true,
    onSuccess(data) {
      const renameList = data.map((item) => ({
        db_name: item,
        rename_cluster_list: [],
        rename_db_name: '',
        target_db_name: item,
      }));
      localValue.value.renameInfoList = renameList;
      renameInfoList.value = renameList;
      conflictDbList.value = data;

      if (data.length > 0) {
        runCheckClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.data.srcCluster.id,
          cluster_ids: props.data.dstCluster.map((item) => item.id),
          db_list: data,
        });
      }
    },
  });

  watch(
    () => ({
      dbIgnoreName: dbIgnoreName.value,
      dbName: dbName.value,
      dstCluster: props.data.dstCluster,
      srcClusterId: props.data.srcCluster.id,
    }),
    ({ dbIgnoreName, dbName, srcClusterId }) => {
      const dbNameChanged = dbName.join(',') !== localValue.value.dbName.join(',');
      const dbIgnoreNameChanged = dbIgnoreName.join(',') !== localValue.value.dbIgnoreName.join(',');
      const srcClusterChanged = currentSrcClusterId !== srcClusterId;

      if (dbNameChanged || dbIgnoreNameChanged || srcClusterChanged) {
        hasEditRename.value = false;
      }

      if (hasEditRename.value) return;

      currentSrcClusterId = srcClusterId;
      localValue.value = { dbIgnoreName, dbName, renameInfoList: [] };

      if (srcClusterId && dbName.length > 0) {
        fetchSqlserverDbs({
          cluster_id: srcClusterId,
          db_list: dbName,
          ignore_db_list: dbIgnoreName,
        });
      }
    },
    { immediate: true },
  );

  const disabledMethod = (rowData: any, field?: string) => {
    if (
      field === 'renameInfoList' &&
      (!rowData.srcCluster.id || rowData.dstCluster.length < 1 || rowData.dbName.length < 1)
    ) {
      return t('请先设置集群、目标集群、构造 DB');
    }
    return '';
  };

  const handleShowEditName = () => {
    if (noConflictDb.value && !hasEditRename.value) {
      return;
    }
    editRenameRef.value?.updateTableKey();
    isShowEditName.value = true;
  };

  const handleSubmit = () => {
    isShowEditName.value = false;
    dbName.value = localValue.value.dbName;
    dbIgnoreName.value = localValue.value.dbIgnoreName;
    renameInfoList.value = localValue.value.renameInfoList;
    hasEditRename.value = true;
    conflictDbList.value = [];
  };
</script>
