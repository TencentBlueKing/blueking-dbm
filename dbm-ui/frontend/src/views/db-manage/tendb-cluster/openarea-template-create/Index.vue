<template>
  <BkLoading :loading="isDetailLoading">
    <SmartAction
      class="spider-openarea-page"
      :offset-target="getSmartActionOffsetTarget">
      <BkForm
        ref="formRef"
        class="spider-template-create-page mb-32"
        :model="formData">
        <DbCard :title="t('基本信息')">
          <BkFormItem
            :label="t('模块名称')"
            property="config_name"
            required>
            <BkInput
              v-model="formData.config_name"
              :maxlength="32"
              :placeholder="t('请输入模板名称')"
              show-word-limit
              style="width: 560px" />
          </BkFormItem>
        </DbCard>
        <DbCard
          class="mt-18"
          property="source_cluster_id"
          :title="t('模板配置')">
          <BkFormItem
            :label="t('源集群')"
            required>
            <BkButton @click="handleShowClusterSelector">
              <DbIcon
                style="margin-right: 3px"
                :type="currentCluster.domain ? 'edit' : 'add'" />
              <span>{{ currentCluster.domain ? t('修改集群') : t('添加源集群') }}</span>
            </BkButton>
            <div
              v-if="currentCluster.domain"
              class="current-cluster-operate">
              {{ currentCluster.domain }}
              <DbIcon
                class="delete-icon ml-8"
                type="delete"
                @click="handleDeleteCurrentCluster" />
            </div>
          </BkFormItem>
          <BkFormItem
            :label="t('克隆的规则')"
            required>
            <ConfigRule
              ref="configRuleRef"
              :cluster-id="formData.source_cluster_id"
              :data="formData.config_rules" />
          </BkFormItem>
          <BkFormItem :label="t('初始化权限规则')">
            <BkButton
              class="mb-12"
              :disabled="formData.source_cluster_id === 0"
              @click="handleShowPermissionRule">
              <DbIcon
                style="margin-right: 3px"
                type="add" />
              <span>{{ t('添加权限') }}</span>
            </BkButton>
            <BKLoading :loading="permissionTableloading">
              <BkTable
                v-if="permissionTableData.length > 0"
                :cell-class="getCellClass"
                class="add-permission-table"
                :columns="permissionTableColumns"
                :data="permissionTableData" />
            </BKLoading>
          </BkFormItem>
        </DbCard>
      </BkForm>
      <ClusterSelector
        v-model:is-show="isShowClusterSelector"
        :cluster-types="[ClusterTypes.TENDBCLUSTER]"
        only-one-type
        :selected="clusterSelectorValue"
        :tab-list-config="tabListConfig"
        @change="handelClusterChange" />
      <PermissionRule
        v-model="permissionRules"
        v-model:is-show="isShowPermissionRule"
        :cluster-id="formData.source_cluster_id"
        db-type="tendbcluster"
        @submit="handleSelectedPermissionRule" />
      <template #action>
        <BkButton
          class="w-88"
          :disabled="!formDataChanged"
          :loading="isSubmiting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          :disabled="!formDataChanged"
          @click="handleReset">
          {{ t('重置') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </template>
    </SmartAction>
  </BkLoading>
</template>
<script setup lang="tsx">
  import { Form } from 'bkui-vue';
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import MysqlPermissonAccountModel from '@services/model/mysql/mysql-permission-account';
  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import { create as createOpenarea, getDetail, update as updateOpenarea } from '@services/source/openarea';
  import { getPermissionRules } from '@services/source/permission';

  import { useBeforeClose } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector, { type TabConfig } from '@components/cluster-selector/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import PermissionRule from '@views/db-manage/common/add-permission-rule-dialog/Index.vue';

  import { messageSuccess } from '@utils';

  import ConfigRule from './components/config-rule/Index.vue';

  type CreateOpenareaParams = ServiceParameters<typeof createOpenarea>;

  const { currentBizId } = useGlobalBizs();

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const handleBeforeClose = useBeforeClose();

  const isEditMode = route.name === 'spiderOpenareaTemplateEdit';

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const genDefaultValue = () => ({
    config_name: '',
    source_cluster_id: 0,
    config_rules: [] as ServiceReturnType<typeof getDetail>['config_rules'],
  });

  const configRuleRef = ref<InstanceType<typeof ConfigRule>>();
  const formRef = ref<InstanceType<typeof Form>>();
  const formData = reactive(genDefaultValue());
  const isSubmiting = ref(false);
  const isShowClusterSelector = ref(false);
  const isShowPermissionRule = ref(false);
  const permissionTableloading = ref(false);
  const permissionRules = ref<number[]>([]);
  const rowFlodMap = ref<Record<string, boolean>>({});
  const permissionTableData = ref<MysqlPermissonAccountModel[]>([]);
  const formDataChanged = ref(false);
  const currentCluster = ref({
    type: 'tendbha',
    domain: '',
  });

  const clusterSelectorValue = shallowRef<Record<string, TendbclusterModel[]>>({
    [ClusterTypes.TENDBCLUSTER]: []
  });

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: {
      multiple: false,
    }
  } as Record<string, TabConfig>;

  const permissionTableColumns = computed(() => [
    {
      label: t('账号名称'),
      field: 'user',
      width: 220,
      showOverflowTooltip: false,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => (
        <div class="account-box">
          {
            data.rules.length > 1
              && <db-icon
                  type="down-shape"
                  class={{
                    'flod-flag': true,
                    'is-flod': rowFlodMap.value[data.account.user],
                  }}
                  onClick={() => handleToogleExpand(data.account.user)} />
          }
          { data.account.user }
        </div>
      ),
    },
    {
      label: t('访问DB'),
      width: 300,
      field: 'access_db',
      showOverflowTooltip: true,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map(item => (
          <div class="inner-row">
            <bk-tag>
              {item.access_db}
            </bk-tag>
          </div>
        ));
      },
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: false,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return <div class="inner-row">--</div>;
        }
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map(item => (
          <div class="inner-row cell-privilege">
            <TextOverflowLayout>
              {{
                default: () => item.privilege
              }}
            </TextOverflowLayout>
          </div>
        ));
      },
    },
    {
      label: t('操作'),
      field: 'operate',
      width: 145,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map(item => (
          <div class="inner-row">
            <bk-button
              text
              theme="primary"
              onClick={() => handleRemoveSelectedPermissionRules(item)}>
              {t('移除')}
            </bk-button>
          </div>
        ));
      }
    },
  ]);

  // 编辑态获取模版详情
  const { loading: isDetailLoading, run: fetchTemplateDetail } = useRequest(getDetail, {
    manual: true,
    async onSuccess(data) {
      formData.config_name = data.config_name;
      formData.source_cluster_id = data.source_cluster_id;
      formData.config_rules = data.config_rules;

      permissionRules.value = data.related_authorize;
      await handleSelectedPermissionRule(data.related_authorize)
    },
  });

  watch(formData, () => {
    window.changeConfirm = true;
    formDataChanged.value = true;
  }, {
    deep: true,
  })

  if (isEditMode) {
    fetchTemplateDetail({
      id: Number(route.params.id),
    });
  }

  const getCellClass = (data: { field: string }) => ['privilege', 'operate'].includes(data.field) ? 'cell-privilege' : '';

  const handleRemoveSelectedPermissionRules = (data: MysqlPermissonAccountModel['rules'][number]) => {
    const permissionIndex = permissionTableData.value.findIndex(item => item.account.account_id === data.account_id)!;
    const permission = permissionTableData.value[permissionIndex];
    const ruleIndex = permission.rules.findIndex(item => item.rule_id === data.rule_id)!;
    if (permission.rules.length === 1) {
      permissionTableData.value.splice(permissionIndex, 1);
    } else {
      permission.rules.splice(ruleIndex, 1);
    }
    const selectedRuleIndex = permissionRules.value.findIndex(id => id === data.rule_id);
    permissionRules.value.splice(selectedRuleIndex, 1);
  }

  const handleSelectedPermissionRule = async (ruleIds: number[]) => {
    if (ruleIds.length === 0) {
      return
    }
    permissionTableloading.value = true;
    const rulesResult = await getPermissionRules({
      offset: 0,
      limit: -1,
      rule_ids: ruleIds.join(','),
      account_type: 'tendbcluster',
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    }).finally(() => {
      permissionTableloading.value = false;
    });
    permissionTableData.value = rulesResult.results;
  }

  const handleToogleExpand = (user: string) => {
    if (rowFlodMap.value[user]) {
      delete rowFlodMap.value[user];
    } else {
      rowFlodMap.value[user] = true;
    }
  };

  const handleShowPermissionRule = () => {
    isShowPermissionRule.value = true;
  }

  const handleShowClusterSelector = () => {
    isShowClusterSelector.value = true;
  };

  const handelClusterChange = (selected: Record<string, TendbclusterModel[]>) => {
    clusterSelectorValue.value = selected;

    const { id, master_domain: domain, cluster_type: clusterType } = selected[ClusterTypes.TENDBCLUSTER][0];
    formData.source_cluster_id = id;
    currentCluster.value = {
      type: clusterType,
      domain,
    };
  };

  const handleDeleteCurrentCluster = () => {
    formData.source_cluster_id = 0;
    currentCluster.value = {
      type: '',
      domain: '',
    };
  }

  const handleSubmit = () => {
    isSubmiting.value = true;
    Promise.all([
      (configRuleRef.value as InstanceType<typeof ConfigRule>).getValue(),
      (formRef.value as InstanceType<typeof Form>).validate(),
    ])
      .then(([configRule]) => {
        const params: CreateOpenareaParams & { id: number } = {
          id: 0,
          bk_biz_id: currentBizId,
          ...formData,
          config_rules: configRule,
          cluster_type: 'tendbcluster',
          related_authorize: permissionRules.value,
        };
        if (isEditMode) {
          params.id = Number(route.params.id);
        }
        const handler = isEditMode ? updateOpenarea : createOpenarea;
        return handler(params).then(() => {
          messageSuccess(isEditMode ? t('编辑成功') : t('新建成功'));
          window.changeConfirm = false;
          router.push({
            name: 'spiderOpenareaTemplate',
          });
        });
      })
      .finally(() => {
        isSubmiting.value = false;
      });
  };

  const handleReset = () => {
    handleDeleteCurrentCluster();
    Object.assign(formData, genDefaultValue());
    permissionTableData.value = [];
    permissionRules.value = [];
    nextTick(() => {
      window.changeConfirm = false;
      formDataChanged.value = false;
    });
  };

  const handleCancel = async () => {
    const result = await handleBeforeClose();
    if (!result) return;
    window.changeConfirm = false;
    router.push({
      name: 'spiderOpenareaTemplate',
    });
  }

  defineExpose({
    routerBack() {
      router.push({
        name: 'spiderOpenareaTemplate',
      });
    },
  });
</script>
<style lang="less">
  .spider-template-create-page {
    .bk-form-label {
      font-size: 12px;
    }

    .current-cluster-operate {
      display: flex;
      margin-top: 12px;
      font-size: 14px;
      align-items: center;

      .delete-icon {
        font-size: 13px;
        color: #3a84ff;
        cursor: pointer;
      }
    }

    .add-permission-table {
      .account-box {
        font-weight: 700;

        .flod-flag {
          display: inline-block;
          margin-right: 4px;
          cursor: pointer;
          transition: all 0.1s;

          &.is-flod {
            transform: rotateZ(-90deg);
          }
        }
      }

      .cell-privilege {
        .cell {
          padding: 0 !important;
          margin-left: -16px;

          .inner-row {
            padding-left: 32px !important;
          }
        }
      }

      .inner-row {
        display: flex;
        height: 40px;
        align-items: center;

        & ~ .inner-row {
          border-top: 1px solid #dcdee5;
        }
      }
    }
  }
</style>
