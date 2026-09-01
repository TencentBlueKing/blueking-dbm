<template>
  <BkPopover
    :is-show="isShowUpdateAlias"
    placement="top"
    theme="light"
    trigger="manual"
    @after-hidden="handlePopoverhide"
    @after-show="handlePopoverShown">
    <div
      class="cluster-alias-name-edit-btn"
      :class="{
        'is-active': isActive,
      }"
      role="table-cell-operation">
      <AuthTemplate
        :action-id="actionId"
        :permission="permission"
        :resource="data.id"
        @click="handleShowEdit">
        <DbIcon
          style="font-size: 16px"
          type="edit" />
      </AuthTemplate>
    </div>
    <template #content>
      <div style="margin-bottom: 8px; font-size: 16px; font-weight: bold">
        {{ t('编辑集群别名') }}
      </div>
      <BkForm
        ref="bkform"
        form-type="vertical"
        :model="formData">
        <BkFormItem
          :label="t('集群别名')"
          property="new_alias"
          required>
          <BkInput
            v-model="formData.new_alias"
            style="width: 300px; margin-top: 8px" />
          <div style="display: flex; margin-top: 8px"></div>
        </BkFormItem>
      </BkForm>
      <div style="display: flex">
        <BkButton
          :loading="isUpdateing"
          size="small"
          style="margin-left: auto"
          theme="primary"
          @click="handleEditAlias">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-8"
          size="small"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { updateClusterAlias } from '@services/source/dbbase';

  import { DBTypes } from '@common/const';

  import { getClusterMetaUpdater } from '../utils/updateK8sClusterMeta';

  interface Props {
    data: {
      cluster_alias: string;
      cluster_name: string;
      cluster_type: string;
      db_type: string;
      id: number;
      permission: Record<string, boolean>;
    };
  }

  const props = defineProps<Props>();

  const emits = defineEmits<(e: 'success') => void>();

  const { t } = useI18n();
  const fromRef = useTemplateRef('bkform');

  const isActive = ref(false);

  const { loading: isUpdateing, run: runUpdateClusterAlias } = useRequest(
    (params: { cluster_id: number; new_alias: string }) => {
      const updater = getClusterMetaUpdater(props.data.cluster_type);
      if (updater) {
        return updater({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_alias: params.new_alias,
          cluster_id: params.cluster_id,
        });
      }
      return updateClusterAlias(params);
    },
    {
      manual: true,
      onSuccess() {
        isShowUpdateAlias.value = false;
        emits('success');
      },
    },
  );

  const formData = reactive({
    new_alias: props.data.cluster_alias,
  });
  const isShowUpdateAlias = ref(false);

  // 数据库类型对应的编辑权限 actionId
  const editActionIdMap: Record<DBTypes, string> = {
    [DBTypes.DORIS]: 'doris_edit',
    [DBTypes.ES]: 'es_edit',
    [DBTypes.HDFS]: 'hdfs_edit',
    [DBTypes.INFLUXDB]: 'influxdb_edit',
    [DBTypes.K8S_QRRANT]: 'k8s_qdrant_edit',
    [DBTypes.K8S_SURREALDB]: 'k8s_surrealdb_edit',
    [DBTypes.KAFKA]: 'kafka_edit',
    [DBTypes.MONGODB]: 'mongodb_edit',
    [DBTypes.MYSQL]: 'mysql_edit',
    [DBTypes.ORACLE]: 'oracle_edit',
    [DBTypes.PULSAR]: 'pulsar_edit',
    [DBTypes.REDIS]: 'redis_edit',
    [DBTypes.RIAK]: 'riak_edit',
    [DBTypes.SQLSERVER]: 'sqlserver_edit',
    [DBTypes.TENDBCLUSTER]: 'tendbcluster_edit',
  };

  const actionId = computed(() => editActionIdMap[props.data.db_type as DBTypes]);
  const permission = computed(() => props.data.permission[actionId.value]);

  const handlePopoverShown = () => {
    formData.new_alias = props.data.cluster_alias;
    isActive.value = true;
  };
  const handlePopoverhide = () => {
    isActive.value = false;
  };
  const handleShowEdit = () => {
    isShowUpdateAlias.value = true;
  };

  const handleEditAlias = () => {
    fromRef.value!.validate().then(() => {
      runUpdateClusterAlias({
        cluster_id: props.data.id,
        ...formData,
      });
    });
  };

  const handleCancel = () => {
    isShowUpdateAlias.value = false;
  };
</script>
<style lang="less">
  .cluster-alias-name-edit-btn {
    display: inline-block;
    padding-left: 4px;
    color: #979ba5;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }

    &.is-active {
      display: inline-block !important;
    }
  }
</style>
