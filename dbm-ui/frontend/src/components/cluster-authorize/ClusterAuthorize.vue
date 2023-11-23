<template>
  <BkSideslider
    :before-close="handleBeforeClose"
    :is-show="isShow"
    :title="$t('添加授权')"
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
          <i class="db-icon-attention-fill" />
          <strong>{{ $t('提交失败_信息校验不通过_失败具体原因如下') }}</strong>
        </div>
        <p
          v-for="(text, index) of state.errors.message"
          :key="index"
          class="error__desc pl-24">
          {{ text }}
        </p>
      </div>
      <DbFormItem
        class="cluster-authorize__bold"
        :label="$t('访问源')"
        property="source_ips"
        required>
        <IpSelector
          :biz-id="globalBizsStore.currentBizId"
          button-text="添加 IP"
          :is-cloud-area-restrictions="false"
          :panel-list="['staticTopo', 'manualInput', 'dbmWhitelist']"
          service-mode="all"
          @change="handleChangeIP"
          @change-whitelist="handleChangeWhitelist" />
      </DbFormItem>
      <BkFormItem
        class="cluster-authorize__bold"
        :label="$t('目标集群')"
        property="target_instances"
        required>
        <BkButton
          class="cluster-authorize__button"
          @click="handleShowTargetCluster">
          <i class="db-icon-add button-icon" />
          {{ $t('添加目标集群') }}
        </BkButton>
        <DBCollapseTable
          v-if="clusterState.tableProps.data.length > 0"
          class="mt-16"
          :operations="clusterState.operations"
          :table-props="clusterState.tableProps"
          :title="clusterTypeTitle" />
      </BkFormItem>
      <h5 class="cluster-authorize__bold cluster-authorize__label pb-16">
        {{ $t('权限规则') }}
      </h5>
      <BkFormItem
        :label="$t('账号名')"
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
        :label="$t('访问DB')"
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
              <i class="db-icon-plus-circle mr-4" />
              {{ $t('跳转新建规则') }}
            </BkButton>
          </template>
        </BkSelect>
      </BkFormItem>
      <BkFormItem :label="$t('权限明细')">
        <DbOriginalTable
          :columns="columns"
          :data="selectedRules"
          :empty-text="$t('请选择访问DB')" />
      </BkFormItem>
    </DbForm>
    <template #footer>
      <BkButton
        class="mr-8"
        :loading="state.isLoading"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <BkButton
        :disabled="state.isLoading"
        @click="handleClose">
        {{ $t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
  <ClusterSelector
    v-model:is-show="clusterState.isShow"
    :cluster-type="clusterType"
    only-one-type
    :selected="clusterSelectorSelected"
    :tab-list="tabList"
    @change="handleClusterSelected" />
</template>
<script lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getPermissionRules, preCheckAuthorizeRules } from '@services/permission';
  import { checkHost } from '@services/source/ipchooser';
  import { createTicket } from '@services/source/ticket';
  import { getWhitelist } from '@services/source/whitelist';
  import type { ResourceItem } from '@services/types';
  import type { AuthorizePreCheckData, PermissionRule } from '@services/types/permission';

  import { useCopy, useInfo, useStickyFooter, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import type { AccountTypesValues } from '@common/const';
  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { getClusterSelectorSelected } from '@components/cluster-selector/ClusterSelector.vue';
  import type { ClusterSelectorResult } from '@components/cluster-selector/types';
  import DBCollapseTable, {
    type ClusterTableProps,
  } from '@components/db-collapse-table/DBCollapseTable.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  export default {
    name: 'ClusterAuthorize',
  };
</script>

<script setup lang="tsx">
  interface Props {
    user?: string,
    accessDbs?: string[],
    selected?: ResourceItem[],
    clusterType?: string,
    accountType?: AccountTypesValues,
    tabList?: string[]
  }

  interface Emits {
    (e: 'success'): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    user: '',
    accessDbs: () => [],
    selected: () => [],
    clusterType: ClusterTypes.TENDBHA,
    accountType: AccountTypes.MYSQL,
    tabList: () => [],
  });
  const emits = defineEmits<Emits>();
  const isShow = defineModel<boolean>({
    required: true,
    default: false,
  });

  const router = useRouter();
  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const formRef = ref();
  /** 设置底部按钮粘性布局 */
  useStickyFooter(formRef);

  const state = reactive({
    isLoading: false,
    errors: {
      isShow: false,
      message: [] as string[],
    },
    formdata: initFormdata(props.user),
  });
  const rules = {
    source_ips: [{
      trigger: 'change',
      message: t('请添加访问源'),
      validator: (value: string[]) => value.length > 0,
    }],
    target_instances: [{
      trigger: 'change',
      message: t('请添加目标集群'),
      validator: (value: string[]) => value.length > 0,
    }],
    user: [{
      required: true,
      trigger: 'blur',
      message: t('请选择账户名'),
    }],
    access_dbs: [{
      trigger: 'blur',
      message: t('请选择访问DB'),
      validator: (value: string[]) => value.length > 0,
    }],
  };

  /**
   * 重置表单数据
   */
  function initFormdata(user = '', accessDbs: string[] = []): AuthorizePreCheckData {
    return {
      access_dbs: [...accessDbs],
      source_ips: [],
      target_instances: [],
      user,
      cluster_type: '',
    };
  }

  /** 权限规则功能 */
  const accountState = reactive({
    isLoading: false,
    rules: [] as PermissionRule[],
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
  const columns = [{
    label: 'DB',
    field: 'access_db',
    showOverflowTooltip: true,
  }, {
    label: t('权限'),
    field: 'privilege',
    showOverflowTooltip: true,
    render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
  }];

  /**
   * 获取账号信息
   */
  function getAccount() {
    accountState.isLoading = true;
    getPermissionRules({ bk_biz_id: globalBizsStore.currentBizId, account_type: props.accountType })
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
  }

  /**
   * 选择账号重置访问 DB
   */
  function handleSelectedUser() {
    state.formdata.access_dbs = [];
  }

  /**
   * ip 选择
   */
  function handleChangeIP(data: ServiceReturnType<typeof checkHost>) {
    state.formdata.source_ips = data.map(item => ({
      ip: item.ip,
      bk_host_id: item.host_id,
      bk_biz_id: item.biz.id,
    }));
  }

  function handleChangeWhitelist(data: ServiceReturnType<typeof getWhitelist>['results']) {
    // 避免与 handleChangeIP 同时修改 source_ips 参数
    nextTick(() => {
      const formatData = data
        .reduce((ips: string[], item) => ips.concat(item.ips), [])
        .map(ip => ({ ip }));
      state.formdata.source_ips.push(...formatData);
    });
  }

  /** 目标集群 */
  const copy = useCopy();

  const clusterState = reactive({
    clusterType: props.clusterType,
    selected: getClusterSelectorSelected(),
    isShow: false,
    tableProps: {
      data: [] as ResourceItem[],
      columns: [{
        label: t('域名'),
        field: 'master_domain',
      }, {
        label: t('集群'),
        field: 'cluster_name',
      }, {
        label: t('所属DB模块'),
        field: 'db_module_name',
      }, {
        label: t('操作'),
        field: 'operation',
        width: 100,
        render: ({ index }: { index: number }) => <bk-button text theme="primary" onClick={() => handleRemoveSelected(index)}>{t('删除')}</bk-button>,
      }],
      pagination: {
        small: true,
      },
    } as unknown as ClusterTableProps,
    operations: [{
      label: t('清除所有'),
      onClick: () => {
        clusterState.tableProps.data = [];
      },
    }, {
      label: t('复制所有域名'),
      onClick: () => {
        const value = clusterState.tableProps.data.map(item => item.master_domain).join('\n');
        copy(value);
      },
    }],
  });
  const clusterSelectorSelected = computed(() => {
    const { selected, clusterType, tableProps } = clusterState;
    selected[clusterType] = tableProps.data;
    return selected;
  });
  const clusterTypeTitle = computed(() => (clusterState.clusterType === ClusterTypes.TENDBHA ? t('主从') : t('单节点')));
  // 获取选中集群
  watch(() => clusterState.tableProps.data, (data) => {
    state.formdata.target_instances = data.map(item => item.master_domain);
  }, { immediate: true, deep: true });
  function handleShowTargetCluster() {
    clusterState.isShow = true;
  }
  /**
   * 选择器返回结果
   */
  function handleClusterSelected(selected: ClusterSelectorResult) {
    const clusterType = Object.keys(selected).find(key => selected[key].length > 0) || ClusterTypes.TENDBHA;
    clusterState.tableProps.data = selected[clusterType];
    clusterState.clusterType = clusterType;
  }

  function handleRemoveSelected(index: number) {
    clusterState.tableProps.data.splice(index, 1);
  }

  /** 初始化信息 */
  watch(isShow, (show) => {
    if (show) {
      getAccount();
      state.formdata = initFormdata(props.user, props.accessDbs);
      clusterState.tableProps.data = _.cloneDeep(props.selected);
      clusterState.clusterType = props.clusterType;
    }
  });

  /**
   * 授权规则前置检测
   */
  async function handleSubmit() {
    await formRef.value.validate();
    const params = {
      ...state.formdata,
      bizId: globalBizsStore.currentBizId,
      cluster_type: clusterState.clusterType,
    };
    state.isLoading = true;
    preCheckAuthorizeRules(params)
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
  }

  const ticketTypeMap = {
    [AccountTypes.MYSQL]: TicketTypes.MYSQL_AUTHORIZE_RULES,
    [AccountTypes.TENDBCLUSTER]: TicketTypes.TENDBCLUSTER_AUTHORIZE_RULES,
  };

  /**
   * 创建授权单据
   */
  function createAuthorizeTicket(uid: string, data: AuthorizePreCheckData) {
    const params = {
      bk_biz_id: globalBizsStore.currentBizId,
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
  }

  function handleBeforeClose() {
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
  }

  /**
   * 关闭授权侧栏 & 重置数据
   */
  async function handleClose() {
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
  }

  /**
   * 跳转新建规则界面
   */
  function handleToCreateRules() {
    const url = router.resolve({ name: 'PermissionRules' });
    window.open(url.href, '_blank');
  }
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
