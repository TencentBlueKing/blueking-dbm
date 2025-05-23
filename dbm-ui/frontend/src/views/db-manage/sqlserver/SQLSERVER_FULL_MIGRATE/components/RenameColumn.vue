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
      <span
        v-if="noConflictDb && hasEditRename"
        style="color: #2dcb56">
        {{ t('已更新') }}
      </span>
      <span v-else-if="noConflictDb">--</span>
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
    v-model:is-show="isShowEditName"
    :data="data"
    @submit="handleSubmit" />
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { batchCheckClusterDatabase } from '@services/source/dbbase';
  import { getSqlserverDbs } from '@services/source/sqlserver';

  import { makeMap } from '@utils';

  import EditRenameInfo, { type IValue } from './edit-rename-info/Index.vue';

  interface Props {
    data: {
      dbIgnoreName: string[];
      dbName: string[];
      dstCluster: {
        id: number;
        master_domain: string;
      }[];
      renameInfoList: IValue[];
      srcCluster: {
        id: number;
        master_domain: string;
      };
    };
  }

  const props = defineProps<Props>();

  const dbName = defineModel<string[]>('dbName', { required: true });
  const dbIgnoreName = defineModel<string[]>('dbIgnoreName', { required: true });
  const renameInfoList = defineModel<IValue[]>({ required: true });

  const { t } = useI18n();

  const isShowEditName = ref(false);
  const conflictDbList = ref<string[]>([]);
  const loading = ref(false);
  const hasEditRename = ref(false);
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

  const disabledMethod = (
    rowData: {
      dbName: string[];
      dstCluster: {
        id: number;
      }[];
      srcCluster: {
        id: number;
      };
    },
    field?: string,
  ) => {
    if (
      field === 'renameInfoList' &&
      (!rowData.srcCluster.id || rowData.dstCluster.length < 1 || rowData.dbName.length < 1)
    ) {
      return t('请先设置集群、目标集群、构造 DB');
    }
    return '';
  };

  const handleShowEditName = () => {
    isShowEditName.value = true;
  };

  const handleSubmit = (data: Pick<Props['data'], 'dbIgnoreName' | 'dbName' | 'renameInfoList'>) => {
    isShowEditName.value = false;
    dbName.value = data.dbName;
    dbIgnoreName.value = data.dbIgnoreName;
    renameInfoList.value = data.renameInfoList;
    conflictDbList.value = [];
    hasEditRename.value = true;
  };

  const fetchData = async () => {
    try {
      loading.value = true;
      if (!props.data.srcCluster.id || dbName.value.length < 1) {
        return;
      }

      const dbs = await getSqlserverDbs({
        cluster_id: props.data.srcCluster.id,
        db_list: dbName.value,
        ignore_db_list: dbIgnoreName.value,
      });

      renameInfoList.value = dbs.map((item) => ({
        db_name: item,
        rename_cluster_list: [],
        rename_db_name: '',
        target_db_name: item,
      }));

      if (dbs.length < 1) {
        return;
      }

      const result = await batchCheckClusterDatabase({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_ids: props.data.dstCluster.map((item) => item.id),
        db_list: dbs,
      });

      conflictDbList.value = Object.keys(
        Object.values(result).reduce<Record<string, true>>((acc, item) => {
          Object.entries(item).forEach(([db, isExist]) => {
            if (isExist) {
              Object.assign(acc, {
                [db]: true,
              });
            }
          });
          return acc;
        }, {}),
      );
    } finally {
      loading.value = false;
    }
  };

  const cloneData = {};

  watch(
    () => ({
      dbIgnoreName: dbIgnoreName.value,
      dbName: dbName.value,
      dstCluster: props.data.dstCluster,
      srcClusterId: props.data.srcCluster.id,
    }),
    (data) => {
      if (_.isEqual(cloneData, data)) {
        hasEditRename.value = false;
      }
      if (hasEditRename.value) return;
      Object.assign(cloneData, data);
      fetchData();
    },
    {
      immediate: true,
    },
  );
</script>
