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
      <span v-if="renameInfoList.length < 1">--</span>
      <template v-else>
        <span
          v-if="hasEditDbName"
          style="color: #2dcb56">
          {{ t('已更新') }}
        </span>
        <I18nT
          v-else
          keypath="n项待修改">
          <span style="padding-right: 4px; font-weight: bold; color: #ea3636">
            {{ renameInfoList.length }}
          </span>
        </I18nT>
      </template>
    </EditableBlock>
  </EditableColumn>
  <BkSideslider
    v-model:is-show="isShowEditName"
    :width="900">
    <template #header>
      <span>{{ t('手动修改迁移的 DB 名') }}</span>
      <BkTag class="ml-8">{{ data.srcCluster.master_domain }}</BkTag>
    </template>
    <EditRenameInfo v-model="localValue" />
    <template #footer>
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleSubmit">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { checkClusterDatabase } from '@services/source/dbbase';
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

  const dbName = defineModel<string[]>('dbName', {
    required: true,
  });

  const dbIgnoreName = defineModel<string[]>('dbIgnoreName', {
    required: true,
  });

  const renameInfoList = defineModel<IValue[]>('renameInfoList', {
    required: true,
  });

  const { t } = useI18n();

  const isShowEditName = ref(false);
  const hasEditDbName = ref(false);
  const localValue = ref(props.data);

  const disabledMethod = (rowData: Props['data'], field?: string) => {
    if (
      field === 'renameInfoList' &&
      (!rowData.srcCluster.id || rowData.dstCluster.length < 1 || rowData.dbName.length < 1)
    ) {
      return t('请先设置集群、目标集群、构造 DB');
    }
    return '';
  };

  const rules = [
    {
      message: t('构造后 DB 名不能为空'),
      trigger: 'change',
      validator: () => renameInfoList.value.length > 0,
    },
    {
      message: t('构造后 DB 名待有冲突更新'),
      trigger: 'change',
      validator: () => hasEditDbName.value,
    },
    {
      message: t('迁移后 DB 和迁移 DB 数量不匹配'),
      trigger: 'change',
      validator: () => {
        const dbIgnoreNameMap = makeMap(dbIgnoreName.value);
        const dbNameList = dbName.value.filter((item) => !/\*/.test(item) && !/%/.test(item) && !dbIgnoreNameMap[item]);
        return dbNameList.length <= renameInfoList.value.length;
      },
    },
  ];

  const dstClusterIdList = computed(() => props.data.dstCluster.map((item) => item.id));

  const { loading, run: runCheckClusterDatabase } = useRequest(checkClusterDatabase, {
    manual: true,
    onSuccess(data) {
      hasEditDbName.value = _.every(Object.values(data), (item) => !item);
    },
  });

  const { run: fetchSqlserverDbs } = useRequest(getSqlserverDbs, {
    manual: true,
    onSuccess(data) {
      renameInfoList.value = data.map((item) => ({
        db_name: item,
        rename_cluster_list: [],
        rename_db_name: '',
        target_db_name: item,
      }));
      if (data.length > 0) {
        runCheckClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_id: props.data.srcCluster.id,
          cluster_ids: dstClusterIdList.value,
          db_list: data,
        });
      }
    },
  });

  watch(
    () => props.data,
    () => {
      localValue.value = props.data;
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [localValue.value.dbName, localValue.value.dbIgnoreName],
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
    {
      immediate: true,
    },
  );

  const handleShowEditName = () => {
    isShowEditName.value = true;
  };

  const handleSubmit = () => {
    isShowEditName.value = false;
    hasEditDbName.value = true;
    dbName.value = localValue.value.dbName;
    dbIgnoreName.value = localValue.value.dbIgnoreName;
    renameInfoList.value = localValue.value.renameInfoList;
  };

  const handleCancel = () => {
    isShowEditName.value = false;
  };
</script>
