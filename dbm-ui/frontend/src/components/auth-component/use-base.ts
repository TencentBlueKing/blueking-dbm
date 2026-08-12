import { computed, onMounted } from 'vue';
import { useRequest } from 'vue-request';

import { simpleCheckAllowed } from '@services/source/iam';

import { permissionDialog } from '@utils';

export interface Props {
  actionId: string;
  bizId?: string | number;
  permission?: string | boolean;
  resource?: string | number;
}

const withBizActionList = [
  'mysql_apply',
  'mysql_account_rule_create',
  'mysql_excel_authorize',
  'mysql_partition_create',
  'mysql_partition_delete',
  'mysql_partition_update',
  'mysql_partition_enable_disable',
  // 聚合权限
  'mysql_manage',
  'mysql_loadbalance_manage',
  'mysql_partition_manage',
  'mysql_openarea_manage',
  'mysql_priv_manage',
  'mysql_rename_database',
  'mysql_truncate_data',
  'mysql_rollback_cluster',
  'tendbcluster_manage',
  'tendbcluster_loadbalance_manage',
  'tendbcluster_partition_manage',
  'tendbcluster_openarea_manage',
  'tendbcluster_priv_manage',
  'tendbcluster_authorize',
  'tendbcluster_rename_database',
  'tendbcluster_truncate_data',
  'tendbcluster_rollback_cluster',
  'tendbcluster_apply',
  'tendbcluster_cluster_clone_rules',
  'tendbcluster_temporary_destroy',
  'redis_cluster_apply',
  'redis_data_structure_manage',
  'es_apply',
  'kafka_apply',
  'hdfs_apply',
  'pulsar_apply',
  'influxdb_apply',
  'notify_group_manage',
  'monitor_policy_manage',
  // 'monitor_policy_view', // 旧权限
  // 'notify_group_create', // 旧权限
  // 'notify_group_update', // 旧权限
  // 'notify_group_list', // 旧权限
  // 'notify_group_delete', // 旧权限
  'dbconfig_view',
  'dbconfig_edit',
  'dba_admin_edit',
  'health_report_view',
  'dbha_switch_event_view',
  'ip_whitelist_manage',
  'group_manage',
  // 查看临时密码权限按 DB 类型拆分（原 admin_pwd_view 已废弃）
  'mysql_admin_pwd_view',
  'sqlserver_admin_pwd_view',
  'riak_cluster_apply',
  // 'monitor_policy_clone', // 旧权限
  'mongodb_apply',
  'mongodb_priv_manage',
  'sqlserver_apply',
  'sqlserver_manage',
  // 'sqlserver_account_create', // 旧权限
  // 'sqlserver_account_rules_view', // 旧权限
  'sqlserver_priv_manage',
  'biz_ticket_config_set',
  'doris_apply',
  'biz_assistance_vars_config',
  'biz_notify_config',
  'mysql_dbconfig_edit',
  'redis_dbconfig_edit',
  'mongodb_dbconfig_edit',
  'sqlserver_dbconfig_edit',
  'tendbcluster_dbconfig_edit',
  'doris_dbconfig_edit',
  'es_dbconfig_edit',
  'kafka_dbconfig_edit',
  'hdfs_dbconfig_edit',
  'pulsar_dbconfig_edit',
  'influxdb_dbconfig_edit',
];

export default function (props: Props) {
  const {
    data: checkResult,
    loading,
    run,
  } = useRequest(simpleCheckAllowed, {
    manual: true,
  });

  const isShowRaw = computed(() => {
    if (props.permission === true) {
      return true;
    }
    return checkResult.value;
  });

  const realParams = computed(() => {
    const params = {
      action_id: props.actionId,
    };

    if (props.resource) {
      Object.assign(params, {
        resource_id: props.resource,
      });
    }

    if (props.bizId !== undefined) {
      Object.assign(params, {
        bk_biz_id: props.bizId,
      });
    } else if (withBizActionList.includes(props.actionId)) {
      Object.assign(params, {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      });
    }

    return params;
  });

  // 检测权限
  const checkPermission = () => {
    if (!props.actionId) {
      return;
    }
    run(realParams.value, { cache: 1000 });
  };

  const handleRequestPermission = (event: Event) => {
    if (loading.value) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    permissionDialog(undefined, realParams.value);
  };

  onMounted(() => {
    // 初始没有权限信息，需要主动鉴权一次
    if (props.permission === 'normal') {
      checkPermission();
    }
  });

  return {
    handleRequestPermission,
    isShowRaw,
    loading,
  };
}
