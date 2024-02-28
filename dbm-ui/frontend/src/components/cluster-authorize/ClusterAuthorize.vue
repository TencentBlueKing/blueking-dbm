<template>
  <BkSideslider
    :before-close="handleBeforeClose"
    :is-show="isShow"
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
        v-if="accountType !== AccountTypes.MONGODB"
        class="cluster-authorize__bold"
        :label="t('访问源')"
        property="source_ips"
        required>
        <IpSelector
          :biz-id="bizId"
          button-text="添加 IP"
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
            columns: collapseTableColumns
          }"
          :title="clusterTypeTitle" />
      </BkFormItem>
      <template v-if="accountType === AccountTypes.MONGODB">
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
          <AccountRulesTable
            v-if="selectedList.length > 0"
            class="mt-16"
            :selected-list="selectedList"
            @delete="handleRowDelete" />
        </BkFormItem>
      </template>
      <template v-else>
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
            v-if="clusterType === ClusterTypes.TENDBHA"
            class="mb-16 mt-10"
            theme="warning"
            :title="t('注意_对从库授权时仅会授予select权限')" />
          <DbOriginalTable
            :columns="permissonColumns"
            :data="selectedRules"
            :empty-text="t('请选择访问DB')" />
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
  <ClusterSelectorNew
    v-if="accountType === AccountTypes.MONGODB"
    v-model:is-show="clusterState.isShow"
    :cluster-types="clusterTypes"
    only-one-type
    :selected="clusterSelectorSelected"
    :tab-list-config="tabListConfig"
    @change="handleNewClusterChange" />
  <MySqlClusterSelector
    v-else
    v-model:is-show="clusterState.isShow"
    :cluster-types="clusterTypes"
    only-one-type
    :selected="clusterSelectorSelected"
    :tab-list="tabList"
    @change="handleClusterSelected" />
  <AccountRulesSelector
    v-model:is-show="accoutRulesShow"
    :selected-list="selectedList"
    @change="handleAccountRulesChange" />
</template>
<script lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import MongodbPermissonAccountModel from '@services/model/mongodb-permission/mongodb-permission-account';
  import {
    getPermissionRules,
    preCheckAuthorizeRules,
  } from '@services/permission';
  import { checkHost } from '@services/source/ipchooser';
  import { getMongodbPermissionRules } from '@services/source/mongodbPermissionAccount';
  import { preCheckMongodbAuthorizeRules } from '@services/source/mongodbPermissionAuthorize';
  import { createTicket } from '@services/source/ticket';
  import { getWhitelist } from '@services/source/whitelist';
  import type {
    AuthorizePreCheckData,
    PermissionRule,
  } from '@services/types/permission';

  import {
    useCopy,
    useInfo,
    useStickyFooter,
    useTicketMessage,
  } from '@hooks';

  import type { AccountTypesValues } from '@common/const';
  import {
    AccountTypes,
    ClusterTypes,
    TicketTypes,
  } from '@common/const';

  import ClusterSelectorNew, {
    type TabConfig,
  } from '@components/cluster-selector-new/Index.vue';
  import DBCollapseTable, {
    type ClusterTableProps,
  } from '@components/db-collapse-table/DBCollapseTable.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import AccountRulesTable from './accouter-rules-selector/components/AccountRulesTable.vue';
  import AccountRulesSelector from './accouter-rules-selector/Index.vue';
  import MySqlClusterSelector, { getClusterSelectorSelected } from './cluster-selector/ClusterSelector.vue';
  import type { ClusterSelectorResult } from './cluster-selector/types';

  export default {
    name: 'ClusterAuthorize',
  };
</script>

<script setup lang="tsx">
  type ResourceItem = NonNullable<Props['selected']>[number] & { isMaster?: boolean };
  type MysqlPreCheckResulst = ServiceReturnType<typeof preCheckAuthorizeRules>
  type MongoPreCheckResulst = ServiceReturnType<typeof preCheckMongodbAuthorizeRules>

  interface Props {
    accountType: AccountTypesValues,
    user?: string,
    accessDbs?: string[],
    selected?: {
      master_domain: string,
      cluster_name: string,
      db_module_name?: string,
    }[],
    clusterTypes?: ClusterTypes[],
    tabList?: string[],
    permissonRuleList?: MongodbPermissonAccountModel[]
  }

  interface Emits {
    (e: 'success'): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    user: '',
    accessDbs: () => [],
    selected: () => [],
    clusterTypes: () => [ClusterTypes.TENDBHA],
    tabList: () => [],
    permissonRuleList: () => [],
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const router = useRouter();
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();
  const copy = useCopy();

  const tabListConfigMap: Record<string, TabConfig> = {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      showPreviewResultTitle: true,
    },
  };

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

  const formRef = ref();
  /** 设置底部按钮粘性布局 */
  useStickyFooter(formRef);

  const accoutRulesShow = ref(false);
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
    rules: [] as PermissionRule[],
  });

  const clusterState = reactive({
    clusterType: props.clusterTypes[0],
    selected: getClusterSelectorSelected(),
    isShow: false,
    tableProps: {
      data: [] as ResourceItem[],
      pagination: {
        small: true,
      },
    } as unknown as ClusterTableProps,
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
    return selected;
  });

  const tabListConfig = computed(() => props.clusterTypes.reduce((prevConfig, clusterTypeItem) => ({
    ...prevConfig,
    [clusterTypeItem]: tabListConfigMap[clusterTypeItem],
  }), {} as Record<string, TabConfig>));

  const ticketTypeMap = {
    [AccountTypes.MYSQL]: TicketTypes.MYSQL_AUTHORIZE_RULES,
    [AccountTypes.TENDBCLUSTER]: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
    [AccountTypes.MONGODB]: TicketTypes.MONGODB_AUTHORIZE,
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
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
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
    };

    apiMap[props.accountType]({
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

  const clusterTypeTitle = computed(() => {
    const clusterTextMap: Record<string, string> = {
      [ClusterTypes.TENDBSINGLE]: t('单节点'),
      [ClusterTypes.TENDBHA]: t('主从'),
      [ClusterTypes.TENDBCLUSTER]: 'Spider',
      [ClusterTypes.MONGO_REPLICA_SET]: t('副本集'),
      [ClusterTypes.MONGO_SHARED_CLUSTER]: t('分片集群'),
    };
    return clusterTextMap[clusterState.clusterType];
  });

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
      if (props.accountType === AccountTypes.MONGODB) {
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
      state.formdata.source_ips.push(...formatData);
    });
  };

  const handleShowTargetCluster = () => {
    clusterState.isShow = true;
  };

  const handleShowAccoutRules = () => {
    accoutRulesShow.value = true;
  };

  /**
   * 选择器返回结果
   */
  const handleClusterSelected = (selected: ClusterSelectorResult) => {
    const clusterType = Object.keys(selected).find(key => selected[key].length > 0) || ClusterTypes.TENDBHA;
    clusterState.tableProps.data = selected[clusterType];
    clusterState.clusterType = clusterType as ClusterTypes;
  };

  const handleNewClusterChange = (selected: Record<string, MongodbModel[]>) => {
    clusterState.tableProps.data = Object.keys(selected).reduce((prev, key) => {
      const dataList = selected[key];
      return [...prev, ...dataList.map(dataItem => ({
        master_domain: dataItem.master_domain,
        cluster_name: dataItem.cluster_name,
      }))];
    }, [] as ResourceItem[]);
  };

  const handleRemoveSelected = (index: number) => {
    clusterState.tableProps.data.splice(index, 1);
  };

  /**
   * 跳转新建规则界面
   */
  const handleToCreateRules = () => {
    const routeMap = {
      [AccountTypes.MYSQL]: 'PermissionRules',
      [AccountTypes.TENDBCLUSTER]: 'spiderPermission',
      [AccountTypes.MONGODB]: 'MongodbPermission',
    };
    const url = router.resolve({ name: routeMap[props.accountType] });
    window.open(url.href, '_blank');
  };

  /**
   * 创建授权单据
   */
  const createAuthorizeTicket = (uid: string, data: MysqlPreCheckResulst['authorize_data'] | MongoPreCheckResulst['authorize_data']) => {
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
    };
    const params = {
      target_instances: formdata.target_instances,
      cluster_type: clusterState.clusterType,
    };

    if (props.accountType === AccountTypes.MONGODB) {
      Object.assign(params, {
        mongo_users: selectedList.value.map(selectedItem => ({
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
      .catch(() => {
        state.isLoading = false;
      });
  };

  const handleBeforeClose = () => {
    if (state.isLoading) return false;

    if (window.changeConfirm) {
      return new Promise((resolve) => {
        useInfo({
          title: t('确认离开当前页'),
          content: t('离开将会导致未保存信息丢失'),
          confirmTxt: t('离开'),
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
