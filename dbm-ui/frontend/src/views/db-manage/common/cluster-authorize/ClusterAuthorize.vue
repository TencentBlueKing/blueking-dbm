<template>
  <BkSideslider
    :before-close="handleBeforeClose"
    class="cluster-authorize-slider"
    :is-show="isShow"
    render-directive="if"
    :title="t('添加授权')"
    :width="960"
    @closed="handleClose">
    <DbForm
      ref="formRef"
      class="cluster-authorize"
      form-type="vertical"
      :model="state.formdata"
      :rules="rules">
      <div
        v-if="state.errors.isShow"
        class="cluster-authorize__error mb-24">
        <div class="error__title">
          <DbIcon type="attention-fill" />
          <strong>{{ t('提交失败_信息校验不通过_失败具体原因如下') }}</strong>
        </div>
        <p
          v-for="(text, index) of state.errors.message"
          :key="index"
          class="error__desc pl-24">
          {{ text }}
        </p>
      </div>
      <DbFormItem
        v-if="isMysql"
        class="cluster-authorize__bold"
        :label="t('访问源')"
        property="source_ips"
        required>
        <IpSelector
          :biz-id="bizId"
          button-text="添加 IP"
          :data="selectedIpList"
          :is-cloud-area-restrictions="false"
          :panel-list="['staticTopo', 'manualInput', 'dbmWhitelist']"
          service-mode="all"
          @change="handleChangeIP"
          @change-whitelist="handleChangeWhitelist" />
      </DbFormItem>
      <BkFormItem
        class="cluster-authorize__bold"
        :label="t('目标集群')"
        property="target_instances"
        required>
        <BkButton
          class="cluster-authorize__button"
          @click="handleShowTargetCluster">
          <DbIcon
            class="button-icon"
            type="db-icon-add" />
          {{ t('添加目标集群') }}
        </BkButton>
        <DBCollapseTable
          v-if="clusterState.tableProps.data.length > 0"
          class="mt-16"
          :operations="clusterState.operations"
          :table-props="{
            ...clusterState.tableProps,
            columns: collapseTableColumns,
          }"
          :title="clusterTypeTitle" />
      </BkFormItem>
      <template v-if="isMysql">
        <h5 class="cluster-authorize__bold cluster-authorize__label pb-16">
          {{ t('权限规则') }}
        </h5>
        <BkFormItem
          :label="t('账号名')"
          property="user"
          required>
          <BkSelect
            v-model="state.formdata.user"
            :clearable="false"
            filterable
            :input-search="false"
            :loading="accountState.isLoading"
            @change="handleSelectedUser">
            <BkOption
              v-for="item of accountState.rules"
              :key="item.account.account_id"
              :label="item.account.user"
              :value="item.account.user" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="t('访问DB')"
          property="access_dbs"
          required>
          <BkSelect
            v-model="state.formdata.access_dbs"
            :clearable="false"
            collapse-tags
            filterable
            :input-search="false"
            :loading="accountState.isLoading"
            multiple
            multiple-mode="tag"
            show-select-all>
            <BkOption
              v-for="item of curRules"
              :key="item.rule_id"
              :label="item.access_db"
              :value="item.access_db" />
            <template #extension>
              <BkButton
                class="to-create-rules"
                text
                @click="handleToCreateRules">
                <DbIcon
                  class="mr-4"
                  type="plus-circle" />
                {{ t('跳转新建规则') }}
              </BkButton>
            </template>
          </BkSelect>
        </BkFormItem>
        <BkFormItem :label="t('权限明细')">
          <BkAlert
            v-if="showTip"
            class="mb-16 mt-10"
            theme="warning"
            :title="t('注意_对从域名授权时仅会授予 select 权限')" />
          <DbOriginalTable
            :columns="permissonColumns"
            :data="selectedRules"
            :empty-text="t('请选择访问DB')" />
        </BkFormItem>
      </template>
      <template v-else>
        <BkFormItem
          class="cluster-authorize__bold"
          :label="t('权限规则')"
          property="mongo_users"
          required>
          <div class="permission-item">
            <BkButton
              class="cluster-authorize__button"
              @click="handleShowAccoutRules">
              <DbIcon
                class="button-icon"
                type="db-icon-add" />
              {{ t('添加账号规则') }}
            </BkButton>
            <BkButton
              v-if="selectedList.length > 0"
              text
              theme="primary"
              @click="handleDeleteAll">
              <DbIcon type="delete" />
              <span class="ml-6">{{ t('全部清空') }}</span>
            </BkButton>
          </div>
          <!-- <AccountRulesTable
            v-if="selectedList.length > 0"
            :account-type="accountType"
            class="mt-16"
            :selected-list="selectedList"
            @delete="handleRowDelete" /> -->
          <AccountRulesTable
            v-if="selectedList.length > 0"
            :account-type="accountType"
            class="mt-16"
            :selected-list="selectedList"
            @delete="handleRowDelete" />
        </BkFormItem>
      </template>
    </DbForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <BkButton
        :disabled="state.isLoading"
        @click="handleClose">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
  <ClusterSelector
    v-model:is-show="clusterState.isShow"
    :cluster-types="clusterTypes"
    only-one-type
    :selected="clusterSelectorSelected"
    :tab-list-config="tabListConfig"
    @change="handleClusterChange" />
  <AccountRulesSelector
    v-model:is-show="accoutRulesShow"
    :account-type="accountType"
    :selected-list="selectedList"
    @change="handleAccountRulesChange" />
</template>
<script lang="tsx">
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import MongodbPermissonAccountModel from '@services/model/mongodb/mongodb-permission-account';
  import SqlserverPermissionAccountModel from '@services/model/sqlserver/sqlserver-permission-account';
  import { checkHost } from '@services/source/ipchooser';
  import { getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import { preCheckMongodbAuthorizeRules } from '@services/source/mongodbPermissionAuthorize';
  import { getPermissionRules, preCheckAuthorizeRules } from '@services/source/permission';
  import { getSqlserverPermissionRules } from '@services/source/sqlserverPermissionAccount';
  import { preCheckSqlserverAuthorizeRules } from '@services/source/sqlserverPermissionAuthorize';
  import { getTendbSlaveClusterList } from '@services/source/tendbcluster';
  import { getTendbhaList, getTendbhaSalveList } from '@services/source/tendbha';
  import { createTicket } from '@services/source/ticket';
  import { getWhitelist } from '@services/source/whitelist';
  import type { AuthorizePreCheckData, PermissionRule } from '@services/types/permission';

  import { useCopy, useTicketMessage } from '@hooks';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import DBCollapseTable from '@components/db-collapse-table/DBCollapseTable.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import AccountRulesTable from './accout-rules-preview-table/Index.vue';
  import AccountRulesSelector from './accouter-rules-selector/Index.vue';

  type ResourceItem = NonNullable<Props['selected']>[number] & { isMaster?: boolean };
  type MysqlPreCheckResulst = ServiceReturnType<typeof preCheckAuthorizeRules>;
  type MongoPreCheckResulst = ServiceReturnType<typeof preCheckMongodbAuthorizeRules>;
  type SqlserverPreCheckResulst = ServiceReturnType<typeof preCheckSqlserverAuthorizeRules>;

  interface Props {
    accountType: AccountTypes;
    user?: string;
    accessDbs?: string[];
    selected?: {
      master_domain: string;
      cluster_name: string;
      db_module_name?: string;
    }[];
    clusterTypes?: string[];
    // tabList?: string[],
    permissonRuleList?: MongodbPermissonAccountModel[];
  }

  interface Emits {
    (e: 'success'): void;
  }

  interface Exposes {
    initSelectorData: (data: {
      clusterType: ClusterTypes;
      clusterList: ResourceItem[];
      sourceIpList: ServiceReturnType<typeof checkHost>;
    }) => void;
  }

  type ClusterSelectorResult = Record<string, Array<ResourceItem>>;
</script>

<script setup lang="tsx">
  const props = withDefaults(defineProps<Props>(), {
    user: '',
    accessDbs: () => [],
    selected: () => [],
    clusterTypes: () => [ClusterTypes.TENDBHA],
    // tabList: () => [],
    permissonRuleList: () => [],
  });

  const emits = defineEmits<Emits>();

  defineOptions({
    name: 'ClusterAuthorize',
  })

  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });


  /**
   * 重置表单数据
   */
  const initFormdata = (user = '', accessDbs: string[] = []): AuthorizePreCheckData & { mongo_users: number } => ({
    access_dbs: [...accessDbs],
    source_ips: [],
    target_instances: [],
    user,
    cluster_type: '',
    mongo_users: 0,
  });

  const router = useRouter();
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();
  const copy = useCopy();

  const tabListConfigMap = {
    tendbhaSlave: {
      name: t('MySQL主从-从域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: any) => {
        params.slave_domain = params.domain;
        delete params.domain;
        return getTendbhaSalveList(params)
      }
    },
    [ClusterTypes.TENDBCLUSTER]: {
      name: t('TendbCluster-主域名'),
      showPreviewResultTitle: true,
    },
    tendbclusterSlave: {
      name: t('TendbCluster-从域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: any) => {
        params.slave_domain = params.domain;
        delete params.domain;
        return getTendbSlaveClusterList(params)
      }
    },
    [ClusterTypes.TENDBHA]: {
      name: t('MySQL主从-主域名'),
      showPreviewResultTitle: true,
      getResourceList: (params: any) => {
        params.master_domain = params.domain;
        delete params.domain;
        return getTendbhaList(params)
      }
    },
    [ClusterTypes.TENDBSINGLE]: {
      name: t('MySQL单节点'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      name: t('单节点集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.SQLSERVER_HA]: {
      name: t('主从集群'),
      showPreviewResultTitle: true,
    },
  } as unknown as Record<string, TabConfig>;

  const formRef = ref();

  const accoutRulesShow = ref(false);
  const selectedIpList = ref<ServiceReturnType<typeof checkHost>>([])

  const selectedList = shallowRef<MongodbPermissonAccountModel[]>([]);

  const state = reactive({
    isLoading: false,
    errors: {
      isShow: false,
      message: [] as string[],
    },
    formdata: initFormdata(props.user),
  });

  /** 权限规则功能 */
  const accountState = reactive({
    isLoading: false,
    rules: [] as PermissionRule[] | MongodbPermissonAccountModel[] | SqlserverPermissionAccountModel[],
  });

  const clusterState = reactive({
    clusterType: props.clusterTypes[0],
    selected: {
      tendbhaSlave: [],
      [ClusterTypes.TENDBHA]: [],
      [ClusterTypes.TENDBSINGLE]: [],
      [ClusterTypes.TENDBCLUSTER]: [],
      tendbclusterSlave: [],
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: []
    } as ClusterSelectorResult,
    isShow: false,
    tableProps: {
      data: [] as ResourceItem[],
      pagination: {
        small: true,
        count: 0,
      },
    },
    operations: [
      {
        label: t('清除所有'),
        onClick: () => {
          clusterState.tableProps.data = [];
        },
      },
      {
        label: t('复制所有域名'),
        onClick: () => {
          const value = clusterState.tableProps.data.map(item => item.master_domain).join('\n');
          copy(value);
        },
      },
    ],
  });

  const showTip = computed(() => props.clusterTypes.some(item => ([ClusterTypes.TENDBHA, ClusterTypes.TENDBCLUSTER] as string[]).includes(item)));

  const isMysql = computed(() => [AccountTypes.MYSQL, AccountTypes.TENDBCLUSTER].includes(props.accountType))

  const collapseTableColumns = computed(() => {
    const columns = [
      {
        label: t('域名'),
        field: 'master_domain',
        render: ({ data }: { data: ResourceItem }) => (
          data.isMaster !== undefined
            ? <div class="domain-column">
                {data.isMaster
                  ? <span class="master-icon">{t('主')}</span>
                  : <span class="slave-icon">{t('从')}</span>}
                <span class="ml-6">{data.master_domain}</span>
              </div>
            : <span>{data.master_domain}</span>
        ),
      },
      {
        label: t('集群'),
        field: 'cluster_name',
      },
      {
        label: t('操作'),
        field: 'operation',
        width: 100,
        render: ({ index }: { index: number }) => (
            <bk-button
              text
              theme="primary"
              onClick={() => handleRemoveSelected(index)}>
              {t('删除')}
            </bk-button>
          ),
      },
    ];

    if (props.accountType !== AccountTypes.MONGODB) {
      columns.splice(2, 0, {
        label: t('所属DB模块'),
        field: 'db_module_name',
      });
    }

    return columns;
  });

  const curRules = computed(() => {
    if (state.formdata.user === '') return [];

    const item = accountState.rules.find(item => item.account.user === state.formdata.user);
    return item?.rules || [];
  });

  const selectedRules = computed(() => {
    if (state.formdata.access_dbs.length === 0) return [];

    return curRules.value.filter(item => state.formdata.access_dbs.includes(item.access_db));
  });

  const clusterSelectorSelected = computed(() => {
    const {
      selected,
      clusterType,
      tableProps,
    } = clusterState;
    selected[clusterType] = tableProps.data;
    return selected as unknown as Record<string, (MongodbModel)[]>;
  });

  const tabListConfig = computed(() => props.clusterTypes.reduce((prevConfig, clusterTypeItem) => ({
    ...prevConfig,
    [clusterTypeItem]: tabListConfigMap[clusterTypeItem],
  }), {} as Record<string, TabConfig>));

  const ticketTypeMap = {
    [AccountTypes.MYSQL]: TicketTypes.MYSQL_AUTHORIZE_RULES,
    [AccountTypes.TENDBCLUSTER]: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
    [AccountTypes.MONGODB]: TicketTypes.MONGODB_AUTHORIZE,
    [AccountTypes.SQLSERVER]: TicketTypes.SQLSERVER_AUTHORIZE_RULES
  };

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const permissonColumns = [
    {
      label: 'DB',
      field: 'access_db',
      showOverflowTooltip: true,
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: true,
      render: ({ cell }: { cell: string }) => {
        if (!cell){
          return '--'
        }
        return cell.replace(/,/g, ', ')
      },
    },
  ];

  const rules = {
    source_ips: [
      {
        trigger: 'change',
        message: t('请添加访问源'),
        validator: (value: string[]) => value.length > 0,
      },
    ],
    target_instances: [
      {
        trigger: 'change',
        message: t('请添加目标集群'),
        validator: (value: string[]) => value.length > 0,
      },
    ],
    mongo_users: [
      {
        trigger: 'change',
        message: t('请添加权限规则'),
        validator: (value: number) => value > 0,
      },
    ],
    user: [
      {
        required: true,
        trigger: 'blur',
        message: t('请选择账户名'),
      },
    ],
    access_dbs: [
      {
        trigger: 'blur',
        message: t('请选择访问DB'),
        validator: (value: string[]) => value.length > 0,
      },
    ],
  };

  /**
   * 获取账号信息
   */
  const getAccount = () => {
    accountState.isLoading = true;

    const apiMap = {
      [AccountTypes.MYSQL]: getPermissionRules,
      [AccountTypes.TENDBCLUSTER]: getPermissionRules,
      [AccountTypes.MONGODB]: getMongodbPermissionRules,
      [AccountTypes.SQLSERVER]: getSqlserverPermissionRules
    };

    apiMap[props.accountType]({
      offset: 0,
      limit: -1,
      bk_biz_id: bizId,
      account_type: props.accountType,
    })
      .then((res) => {
        accountState.rules = res.results;
        // 只有一个则直接默认选中
        if (curRules.value.length === 1) {
          state.formdata.access_dbs = [curRules.value[0].access_db];
        }
      })
      .finally(() => {
        accountState.isLoading = false;
      });
  };

  const clusterTypeTitle = computed(() => tabListConfigMap[clusterState.clusterType].name);

  // 获取选中集群
  watch(() => clusterState.tableProps.data, (data) => {
    state.formdata.target_instances = data.map(item => item.master_domain);
  }, {
    immediate: true,
    deep: true,
  });

  /** 初始化信息 */
  watch(isShow, (show) => {
    if (show) {
      getAccount();
      state.formdata = initFormdata(props.user, props.accessDbs);
      clusterState.tableProps.data = _.cloneDeep(props.selected);
      const [clusterType] = props.clusterTypes;
      clusterState.clusterType = clusterType;
      state.formdata.target_instances = props.selected.map(item => item.master_domain);
      if ([AccountTypes.MONGODB, AccountTypes.SQLSERVER].includes(props.accountType)) {
        selectedList.value = props.permissonRuleList
          .map(permissonItem => Object.assign({}, permissonItem, { isExpand: true }));
      }
    }
  });

  watch(selectedList, (newSelectedList) => {
    state.formdata.mongo_users = newSelectedList.length;
  });

  /**
   * 选择账号重置访问 DB
   */
  const handleSelectedUser = () => {
    state.formdata.access_dbs = [];
  };

  /**
   * ip 选择
   */
  const handleChangeIP = (data: ServiceReturnType<typeof checkHost>) => {
    selectedIpList.value = data;
    state.formdata.source_ips = data.map(item => ({
      ip: item.ip,
      bk_host_id: item.host_id,
      bk_biz_id: item.biz.id,
    }));
  };

  const handleChangeWhitelist = (data: ServiceReturnType<typeof getWhitelist>['results']) => {
    // 避免与 handleChangeIP 同时修改 source_ips 参数
    nextTick(() => {
      const formatData = data
        .reduce((ips: string[], item) => ips.concat(item.ips), [])
        .map(ip => ({ ip }));
      state.formdata.source_ips!.push(...formatData);
    });
  };

  const handleShowTargetCluster = () => {
    clusterState.isShow = true;
  };

  const handleShowAccoutRules = () => {
    accoutRulesShow.value = true;
  };

  const handleClusterChange = (selected: ClusterSelectorResult) => {
    const list: ResourceItem[] = [];
    Object.keys(selected).forEach((key) => {
      if (selected[key].length > 0) {
        clusterState.clusterType = key;
      }
      list.push(...selected[key]);
    });
    clusterState.tableProps.data = list;
    clusterState.tableProps.pagination.count = list.length;
    clusterState.selected = selected;
  };

  const handleRemoveSelected = (index: number) => {
    clusterState.tableProps.data.splice(index, 1);
    clusterState.tableProps.pagination.count = clusterState.tableProps.pagination.count - 1;
  };

  /**
   * 跳转新建规则界面
   */
  const handleToCreateRules = () => {
    const routeMap = {
      [AccountTypes.MYSQL]: 'PermissionRules',
      [AccountTypes.TENDBCLUSTER]: 'spiderPermission',
      [AccountTypes.MONGODB]: 'MongodbPermission',
      [AccountTypes.SQLSERVER]: 'SqlServerPermissionRules'
    };
    const url = router.resolve({ name: routeMap[props.accountType] });
    window.open(url.href, '_blank');
  };

  /**
   * 创建授权单据
   */
  const createAuthorizeTicket = (
    uid: string,
    data: MysqlPreCheckResulst['authorize_data'] | MongoPreCheckResulst['authorize_data'] | SqlserverPreCheckResulst['authorize_data']
  ) => {
    const params = {
      bk_biz_id: bizId,
      details: {
        authorize_uid: uid,
        authorize_data: data,
      },
      remark: '',
      ticket_type: ticketTypeMap[props.accountType],
    };

    createTicket(params)
      .then((res) => {
        ticketMessage(res.id);
        nextTick(() => {
          emits('success');
          window.changeConfirm = false;
          handleClose();
        });
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  /**
   * 授权规则前置检测
   */
  const handleSubmit = async () => {
    await formRef.value.validate();

    const { formdata } = state;
    const apiMap = {
      [AccountTypes.MYSQL]: preCheckAuthorizeRules,
      [AccountTypes.TENDBCLUSTER]: preCheckAuthorizeRules,
      [AccountTypes.MONGODB]: preCheckMongodbAuthorizeRules,
      [AccountTypes.SQLSERVER]: preCheckSqlserverAuthorizeRules
    };

    let {clusterType} = clusterState;

    if (clusterState.clusterType === 'tendbhaSlave') {
      clusterType = 'tendbha'
    } else if (clusterState.clusterType === 'tendbclusterSlave') {
      clusterType = 'tendbcluster'
    }

    const params = {
      target_instances: formdata.target_instances,
      cluster_type: clusterType,
    };

    if (props.accountType === AccountTypes.MONGODB) {
      Object.assign(params, {
        mongo_users: selectedList.value.map(selectedItem => ({
          user: selectedItem.account.user,
          access_dbs: selectedItem.rules.map(mapItem => mapItem.access_db),
        })),
      });
    } else if (props.accountType === AccountTypes.SQLSERVER) {
      Object.assign(params, {
        sqlserver_users: selectedList.value.map(selectedItem => ({
          user: selectedItem.account.user,
          access_dbs: selectedItem.rules.map(mapItem => mapItem.access_db),
        })),
      });
    } else {
      Object.assign(params, {
        access_dbs: formdata.access_dbs,
        user: formdata.user,
        source_ips: formdata.source_ips,
        bizId,
      });
    }

    state.isLoading = true;
    apiMap[props.accountType](params)
      .then((res) => {
        const {
          pre_check: preCheck,
          authorize_uid: uid,
          authorize_data: data,
          message,
        } = res;
        if (preCheck) {
          createAuthorizeTicket(uid, data);
          state.errors.isShow = false;
          state.errors.message = [];
          return;
        }
        state.errors.isShow = true;
        state.errors.message = message.split('\n');
        state.isLoading = false;
      })
      .finally(() => {
        state.isLoading = false;
      });
  };

  const handleBeforeClose = () => {
    if (state.isLoading) return false;

    if (window.changeConfirm) {
      return new Promise<boolean>((resolve) => {
        InfoBox({
          title: t('确认离开当前页'),
          content: t('离开将会导致未保存信息丢失'),
          confirmText: t('离开'),
          onConfirm: () => {
            window.changeConfirm = false;
            resolve(true);
            return true;
          },
        });
      });
    }
    return true;
  };

  const handleAccountRulesChange = (value: MongodbPermissonAccountModel[]) => {
    selectedList.value = value;
  };

  const handleRowDelete = (value: MongodbPermissonAccountModel[]) => {
    selectedList.value = value;
  };

  const handleDeleteAll = () => {
    selectedList.value = [];
  };

  /**
   * 关闭授权侧栏 & 重置数据
   */
  const handleClose = async () => {
    const result = await handleBeforeClose();
    if (!result) return;

    clusterState.clusterType = ClusterTypes.TENDBHA;
    clusterState.tableProps.data = [];
    state.formdata = initFormdata();
    state.errors = {
      isShow: false,
      message: [],
    };
    window.changeConfirm = false;
    isShow.value = false;
  };

  defineExpose<Exposes>({
    initSelectorData(data: Parameters<Exposes['initSelectorData']>[number]) {
      nextTick(() => {
        const {
          clusterType,
          clusterList,
          sourceIpList,
        } = data;

        clusterState.clusterType = clusterType;
        clusterState.tableProps.data = clusterList;
        state.formdata.source_ips = sourceIpList.map(item => ({
          ip: item.ip,
          bk_host_id: item.host_id,
          bk_biz_id: item.biz.id,
        }));
        selectedIpList.value = sourceIpList;
      });
    },
  });
</script>

<style lang="less" scoped>
  .cluster-authorize {
    padding: 28px 40px;

    &__error {
      position: sticky;
      top: 0;
      z-index: 10;
      padding: 8px;
      font-size: @font-size-mini;
      background: #ffeded;
      border: 1px solid #ffd2d2;
      border-radius: 2px;

      .error__title {
        padding-bottom: 8px;
        color: @danger-color;

        i > {
          margin-right: 8px;
          font-size: @font-size-large;
        }
      }
    }

    &__bold {
      :deep(.bk-form-label),
      &.cluster-authorize__label {
        font-weight: bold;
        color: @title-color;
      }
    }

    &__button {
      .button-icon {
        margin-right: 4px;
        color: @gray-color;
      }
    }

    .permission-item {
      display: flex;
      justify-content: space-between;

      i {
        font-size: 16px;
      }
    }
  }

  .to-create-rules {
    display: inline-block;
    margin-left: 16px;
    line-height: 40px;

    i {
      color: @gray-color;
    }

    &:hover {
      color: @primary-color;

      i {
        color: @primary-color;
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
