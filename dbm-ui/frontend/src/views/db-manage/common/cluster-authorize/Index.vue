<template>
  <BkSideslider
    :before-close="handleBeforeClose"
    class="cluster-authorize-slider"
    :is-show="isShow"
    render-directive="if"
    :title="t('添加授权')"
    :width="960"
    @closed="handleClose">
    <ErrorMessage :message="state.errorMessage" />
    <Component
      :is="comMap[accountType]"
      ref="dbComRef"
      v-bind="props" />
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <RulesPreview
        v-if="[AccountTypes.MYSQL, AccountTypes.TENDBCLUSTER].includes(accountType) && dbComRef"
        :account-type="(accountType as AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER)"
        :data="dbComRef?.formData" />
      <BkButton
        class="ml-8"
        :disabled="state.isLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { preCheckAuthorizeRules as preCheckMongodbAuthorizeRules } from '@services/source/mongodbPermissionAuthorize';
  import { preCheckAuthorizeRules as preCheckMysqlAuthorizeRules } from '@services/source/mysqlPermissionAuthorize';
  import { preCheckAuthorizeRules as preCheckSqlserverAuthorizeRules } from '@services/source/sqlserverPermissionAuthorize';
  import { createTicket } from '@services/source/ticket';
  import type { HostInfo, PermissionRule } from '@services/types';

  import { useBeforeClose, useTicketMessage } from '@hooks';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import ErrorMessage from './components/ErrorMessage.vue';
  import RulesPreview from './components/RulesPreview.vue';
  import MongoForm from './db-form/Mongo.vue';
  import MysqlForm from './db-form/Mysql.vue';
  import SqlserverForm from './db-form/Sqlserver.vue';
  import TendbclusterForm from './db-form/Tendbcluster.vue';

  interface Props {
    accountType: AccountTypes;
    user?: string;
    accessDbs?: string[];
    selected?: {
      master_domain: string;
      cluster_name: string;
      cluster_type: ClusterTypes;
      db_module_name?: string;
      isMaster?: boolean;
    }[];
    clusterTypes?: string[];
    rules?: PermissionRule['rules'];
  }

  interface Emits {
    (e: 'success'): void;
  }

  interface Exposes {
    init: (data: {
      clusterType: ClusterTypes;
      clusterList: NonNullable<Props['selected']>;
      sourceIpList: HostInfo[];
    }) => void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  defineOptions({
    name: 'ClusterAuthorize',
  });

  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();
  const handleBeforeClose = useBeforeClose();

  const comMap = {
    [AccountTypes.MYSQL]: MysqlForm,
    [AccountTypes.TENDBCLUSTER]: TendbclusterForm,
    [AccountTypes.MONGODB]: MongoForm,
    [AccountTypes.SQLSERVER]: SqlserverForm,
  };

  const state = reactive({
    isLoading: false,
    errorMessage: '',
  });
  const dbComRef = ref();

  const { run: createTicketRun } = useRequest(createTicket, {
    manual: true,
    onSuccess: (res) => {
      ticketMessage(res.id);
      nextTick(() => {
        emits('success');
        window.changeConfirm = false;
        handleClose();
      });
    },
  });

  /**
   * 授权规则前置检测
   */
  const handleSubmit = async () => {
    const { ticketType, params } = await dbComRef.value.getValue();

    const apiMap = {
      [AccountTypes.MYSQL]: preCheckMysqlAuthorizeRules,
      [AccountTypes.TENDBCLUSTER]: preCheckMysqlAuthorizeRules,
      [AccountTypes.MONGODB]: preCheckMongodbAuthorizeRules,
      [AccountTypes.SQLSERVER]: preCheckSqlserverAuthorizeRules,
    };

    try {
      state.isLoading = true;
      const {
        pre_check: preCheck,
        authorize_uid: uid,
        authorize_data: data,
        message,
      } = await apiMap[props.accountType](params);
      if (preCheck) {
        createTicketRun({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            authorize_uid: uid,
            authorize_data: data,
          },
          remark: '',
          ticket_type: ticketType,
        });
        state.errorMessage = '';
        return;
      }
      state.errorMessage = message;
    } finally {
      state.isLoading = false;
    }
  };

  /**
   * 关闭授权侧栏 & 重置数据
   */
  const handleClose = async () => {
    const result = await handleBeforeClose();

    if (!result) {
      return;
    }

    state.errorMessage = '';
    window.changeConfirm = false;
    isShow.value = false;
  };

  defineExpose<Exposes>({
    init(data: Parameters<Exposes['init']>[number]) {
      if (props.accountType === AccountTypes.MYSQL) {
        dbComRef.value.init(data);
      }
    },
  });
</script>

<style lang="less" scoped>
  .cluster-authorize {
    padding: 28px 40px;

    .cluster-authorize-bold {
      :deep(.bk-form-label),
      &.cluster-authorize-label {
        font-weight: bold;
        color: @title-color;
      }
    }

    .cluster-authorize-button {
      .button-icon {
        margin-right: 4px;
        color: @gray-color;
      }
    }
  }
</style>
<style lang="less">
  .cluster-authorize-slider {
    .bk-modal-content {
      max-height: calc(100vh - 125px);
      overflow-y: auto;
    }
  }
</style>
