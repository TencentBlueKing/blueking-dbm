import { computed, onMounted } from 'vue';
import { useRequest } from 'vue-request';

import { simpleCheckAllowed } from '@services/source/iam';

import { permissionDialog } from '@utils';

export interface Props {
  permission?: string | boolean;
  actionId: string;
  resource?: string | number;
  bizId?: string | number;
}

const withBizActionList = [
  'mysql_apply',
  'mysql_account_create',
  'mysql_account_delete',
  'mysql_account_rule_create',
  'mysql_excel_authorize',
  'mysql_partition_create',
  'mysql_partition_delete',
  'mysql_partition_update',
  'mysql_partition_create',
  'mysql_partition_enable_disable',
  'tendbcluster_apply',
  'tendbcluster_account_create',
  'tendbcluster_account_delete',
  'tendbcluster_add_account_rule',
  'tendb_excel_authorize_rules',
  'tendbcluster_cluster_clone_rules',
  'tendbcluster_temporary_destroy',
  'tendbcluster_partition_create',
  'tendbcluster_partition_delete',
  'tendbcluster_partition_update',
  'tendbcluster_partition_create',
  'tendb_partition_enable_disable',
  'tendbcluster_partition',
  'redis_cluster_apply',
  'redis_data_structure_manage',
  'es_apply',
  'kafka_apply',
  'hdfs_apply',
  'pulsar_apply',
  'influxdb_apply',
  'monitor_policy_view',
  'notify_group_create',
  'notify_group_update',
  'notify_group_list',
  'notify_group_create',
  'notify_group_delete',
  'dbconfig_view',
  'dbconfig_edit',
  'dba_administrator_edit',
  'health_report_view',
  'dbha_switch_event_view',
  'ip_whitelist_manage',
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
      resource_ids: props.resource ? [props.resource] : [],
    };

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
    run(realParams.value);
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
    loading,
    isShowRaw,
    handleRequestPermission,
  };
}
