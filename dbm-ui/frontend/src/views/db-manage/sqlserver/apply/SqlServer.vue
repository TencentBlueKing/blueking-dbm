<template>
  <SmartAction :offset-target="getSmartActionOffsetTarget">
    <div class="apply-sqlserver-instance">
      <DbForm
        ref="formRef"
        auto-label-width
        class="apply-form"
        :model="formData"
        :rules="rules">
        <DbCard :title="t('部署模块')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            perrmision-action-id="sqlserver_apply"
            @change-biz="handleChangeBiz" />
          <ModuleItem
            ref="moduleItemRef"
            v-model="formData.details.db_module_id"
            v-model:module-alias-name="moduleAliasName"
            v-model:module-level-config="moduleLevelConfig"
            :biz-id="formData.bk_biz_id"
            :cluster-type="clusterType" />
          <CloudItem
            v-model="formData.details.bk_cloud_id"
            @change="handleChangeCloud" />
        </DbCard>
        <RegionRequirements
          ref="regionRequirements"
          v-model="formData.details"
          :type="isSingleType ? 'single' : 'common'" />
        <DbCard :title="t('数据库部署信息')">
          <BkFormItem
            :label="t('SQLServer起始端口')"
            property="details.start_mssql_port"
            required>
            <BkInput
              v-model="formData.details.start_mssql_port"
              class="item-input"
              :max="65535"
              :min="1025"
              type="number" />
            <span class="ml-10">{{ t('默认从起始端口开始分配') }}</span>
          </BkFormItem>
        </DbCard>
        <DbCard :title="t('需求信息')">
          <BkFormItem
            :label="t('集群数量')"
            property="details.cluster_count"
            required>
            <BkInput
              v-model="formData.details.cluster_count"
              class="item-input"
              :min="1"
              :placeholder="t('请输入')"
              type="number" />
          </BkFormItem>
          <BkFormItem
            :label="t('每组主机部署集群')"
            property="details.inst_num"
            required>
            <BkInput
              v-model="formData.details.inst_num"
              class="item-input"
              :max="Math.max(formData.details.cluster_count, 1)"
              :min="1"
              type="number" />
          </BkFormItem>
          <BkFormItem
            class="service"
            :label="t('域名设置')"
            required>
            <DomainTable
              v-model:domains="formData.details.domains"
              :db-app-abbr="formData.details.db_app_abbr"
              :is-sqlserver-single="isSingleType"
              :module-alias-name="moduleAliasName" />
          </BkFormItem>
          <BkFormItem
            :label="t('服务器选择')"
            property="details.ip_source"
            required>
            <BkRadioGroup
              v-model="formData.details.ip_source"
              class="item-input">
              <BkRadioButton label="resource_pool">
                {{ t('自动从资源池匹配') }}
              </BkRadioButton>
              <!-- <BkRadioButton label="manual_input">
                {{ t('手动录入IP') }}
              </BkRadioButton> -->
            </BkRadioGroup>
          </BkFormItem>
          <Transition
            mode="out-in"
            name="dbm-fade">
            <div
              v-if="formData.details.ip_source === 'manual_input'"
              class="mb-24">
              <DbFormItem
                ref="backendRef"
                :label="isSingleType ? t('服务器') : 'Master / Slave'"
                property="details.nodes.backend"
                required>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.backend"
                  :disable-dialog-submit-method="backendHost"
                  :disable-host-method="disableHostMethod"
                  :disable-tips="formData.details.db_module_id !== null ? '' : t('请选择模块')"
                  @change="handleBackendIpChange">
                  <template #desc>
                    {{ t('需n台', { n: hostNums }) }}
                  </template>
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="需n台_已选n台"
                      style="font-size: 14px; color: #63656e"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56">
                        {{ hostNums }}
                      </span>
                      <span style="font-weight: bold; color: #3a84ff">
                        {{ hostList.length }}
                      </span>
                    </I18nT>
                  </template>
                </IpSelector>
              </DbFormItem>
            </div>
            <div
              v-else
              class="mb-24">
              <BkFormItem
                :label="t('后端存储资源规格')"
                property="details.resource_spec.backend_group.spec_id"
                required>
                <SpecSelector
                  ref="specBackendRef"
                  v-model="formData.details.resource_spec.backend_group.spec_id"
                  :biz-id="formData.bk_biz_id"
                  :city="formData.details.city_code"
                  :cloud-id="formData.details.bk_cloud_id"
                  cluster-type="sqlserver"
                  machine-type="sqlserver"
                  style="width: 435px" />
              </BkFormItem>
            </div>
          </Transition>
          <EstimatedCost
            :params="{
              db_type: DBTypes.SQLSERVER,
              resource_spec: resourceSepc,
            }" />
          <BkFormItem :label="t('备注')">
            <BkInput
              v-model="formData.remark"
              :maxlength="100"
              :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
              style="width: 655px"
              type="textarea" />
          </BkFormItem>
        </DbCard>
      </DbForm>
    </div>
    <template #action>
      <div>
        <BkButton
          class="w-88"
          :loading="baseState.isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          :loading="baseState.isSubmitting"
          @click="() => (isShowPreview = true)">
          {{ t('预览') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          :disabled="baseState.isSubmitting"
          @click="handleResetFormdata">
          {{ t('重置') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          :disabled="baseState.isSubmitting"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
  <!-- 预览功能 -->
  <BkDialog
    v-model:is-show="isShowPreview"
    header-align="left"
    :width="1180">
    <template #header>
      {{ t('实例预览') }}
      <span class="apply-dialog-quantity">
        {{ t('共n条', { n: formData.details.cluster_count }) }}
      </span>
    </template>
    <PreviewTable
      :data="previewData"
      :is-show-nodes="formData.details.ip_source === 'manual_input'"
      :is-single-type="isSingleType"
      :node-list="previewNodes" />
    <template #footer>
      <BkButton @click="() => (isShowPreview = false)">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import InfoBox from 'bkui-vue/lib/info-box';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRoute } from 'vue-router';

  import type { BizItem, HostInfo } from '@services/types';

  import { useApplyBase } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { Affinity, ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import CloudItem from '@views/db-manage/common/apply-items/CloudItem.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import ModuleItem from '@views/db-manage/common/apply-items/ModuleItem.vue';
  import RegionRequirements from '@views/db-manage/common/apply-items/region-requirements/Common.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';

  import DomainTable from './components/DomainTable.vue';
  import PreviewTable from './components/PreviewTable.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();

  const isSingleType = route.name === 'SqlServiceSingleApply';

  const clusterType = isSingleType ? ClusterTypes.SQLSERVER_SINGLE : ClusterTypes.SQLSERVER_HA;

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const getDefaultformData = () => ({
    bk_biz_id: currentBizId,
    details: {
      bk_cloud_id: 0,
      city_code: '',
      cluster_count: 1,
      db_app_abbr: '', // 业务 Code
      db_module_id: null as null | number,
      disaster_tolerance_level: Affinity.NONE, // 容灾
      domains: [{ key: '' }],
      inst_num: 1,
      ip_source: 'resource_pool',
      nodes: {
        backend: [] as HostInfo[],
      },
      resource_spec: {
        backend_group: {
          // spec_cluster_type: 'mysql',
          // spec_machine_type: 'backend',
          affinity: '',
          count: 0,
          location_spec: {
            city: '', // 城市
            sub_zone_ids: [],
          },
          spec_id: '',
          spec_name: '',
        },
      },
      start_mssql_port: 48322, // SQLServer起始端口
      sub_zone_ids: [] as number[],
    },
    remark: '',
    ticket_type: isSingleType ? TicketTypes.SQLSERVER_SINGLE_APPLY : TicketTypes.SQLSERVER_HA_APPLY,
  });

  const regionRequirementsRef = useTemplateRef('regionRequirements');

  const formRef = ref();
  const backendRef = ref();
  const moduleItemRef = ref<InstanceType<typeof ModuleItem>>();
  const isShowPreview = ref(false);
  const specBackendRef = ref<InstanceType<typeof SpecSelector>>();
  const moduleAliasName = ref('');
  const moduleLevelConfig = ref({
    charset: '',
    dbVersion: '',
    systemVersionList: [] as string[],
  });

  const cloudInfo = ref<{
    id: string | number;
    name: string;
  }>({
    id: '',
    name: '',
  });

  const formData = reactive(getDefaultformData());

  const rules = computed(() => ({
    'details.db_app_abbr': [
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',
      },
    ],
    'details.nodes.backend': [
      {
        message: t('请添加服务器'),
        trigger: 'change',
        validator: () => formData.details.nodes.backend.length !== 0,
      },
    ],
  }));

  const resourceSpecbackendGroupCount = computed(() =>
    Math.ceil(formData.details.cluster_count / formData.details.inst_num),
  );
  const hostNums = computed(() =>
    isSingleType ? resourceSpecbackendGroupCount.value : resourceSpecbackendGroupCount.value * 2,
  );

  /**
   * 预览功能
   */
  const previewNodes = computed(() =>
    formData.details.nodes.backend.map((host) => ({
      bk_biz_id: host.biz.id,
      bk_cloud_id: host.cloud_id,
      bk_host_id: host.host_id,
      ip: host.ip,
    })),
  );

  const tableData = computed(() => {
    if (moduleAliasName.value && formData.details.db_app_abbr) {
      return formData.details.domains;
    }
    return [];
  });

  const previewData = computed(() => {
    const { charset, dbVersion } = moduleLevelConfig.value;
    return tableData.value.reduce(
      (accumulator, { key }) => [
        ...accumulator,
        {
          charset,
          deployStructure: isSingleType ? t('单节点部署') : t('主从部署'),
          disasterDefence: t('同城跨园区'),
          domain: `${moduleAliasName.value}db.${key}.${formData.details.db_app_abbr}.db`,
          slaveDomain: `${moduleAliasName.value}db.${key}.${formData.details.db_app_abbr}.db`,
          version: dbVersion,
        },
      ],
      [] as {
        charset: string;
        deployStructure: string;
        disasterDefence: string;
        domain: string;
        slaveDomain: string;
        version: string;
      }[],
    );
  });

  const resourceSepc = computed(
    () =>
      ({
        backend_group: {
          count: resourceSpecbackendGroupCount.value,
          spec_id: formData.details.resource_spec.backend_group.spec_id,
        },
      }) as ComponentProps<typeof EstimatedCost>['params']['resource_spec'],
  );

  /**
   * 设置 domain 数量
   */
  watch(
    () => formData.details.cluster_count,
    (count: number) => {
      const len = formData.details.domains.length;
      if (count === len) {
        return;
      }
      if (count > 0 && count <= 200) {
        if (count > len) {
          const appends = Array.from({ length: count - len }, () => ({ key: '' }));
          formData.details.domains.push(...appends);
        }
        if (count < len) {
          formData.details.domains.splice(count - 1, len - count);
        }
      }
    },
  );

  const backendHost = (hostList: Array<HostInfo>) =>
    hostList.length !== hostNums.value ? t('xx共需n台', { n: hostNums.value, title: 'Master / Slave' }) : false;

  // 只能选择 module 配置中对应操作系统版本的机器
  const disableHostMethod = (data: HostInfo) => {
    const osName = data.os_name.replace(/\s+/g, '');
    const { systemVersionList } = moduleLevelConfig.value;
    return systemVersionList.every((versionItem) => !osName.includes(versionItem))
      ? t('操作系统版本不符合模块配置')
      : false;
  };

  // const getModulesConfig = () => {
  //   fetchModulesConfig({
  //     cluster_type: clusterType,
  //     bk_biz_id: Number(formData.bk_biz_id),
  //   });
  // };

  /**
   * 变更所属管控区域
   */
  const handleChangeCloud = (info: { id: number | string; name: string }) => {
    cloudInfo.value = info;
    formData.details.nodes.backend = [];
  };

  /**
   * 更新 Backend
   */
  const handleBackendIpChange = (data: HostInfo[]) => {
    formData.details.nodes.backend = data;
    if (data.length > 0) {
      backendRef.value.clearValidate();
    }
  };

  const formatNodes = (hosts: HostInfo[]) =>
    hosts.map((host) => ({
      bk_biz_id: host.biz.id,
      bk_cloud_id: host.cloud_id,
      bk_host_id: host.host_id,
      ip: host.ip,
    }));

  /**
   * 提交申请
   */
  const handleSubmit = async () => {
    await formRef.value.validate();
    baseState.isSubmitting = true;
    const getDetails = () => {
      const { details } = formData;

      const resourceSpecKey = isSingleType ? 'backend' : 'backend_group';
      if (details.ip_source === 'resource_pool') {
        return {
          ...details,
          nodes: undefined,
          resource_spec: {
            [resourceSpecKey]: {
              spec_id: details.resource_spec.backend_group.spec_id,
              ...specBackendRef.value!.getData(),
              ...regionRequirementsRef.value!.getValue(),
              count: resourceSpecbackendGroupCount.value,
              spec_cluster_type: clusterType,
              spec_machine_type: clusterType,
            },
          },
        };
      }

      return {
        ...details,
        nodes: {
          backend: formatNodes(details.nodes.backend),
        },
        resource_spec: undefined,
      };
    };
    const params = {
      ...formData,
      details: getDetails(),
    };
    // 若业务没有英文名称则先创建业务英文名称再创建单据，反正直接创建单据
    bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
  };

  /**
   * 重置表单
   */
  const handleResetFormdata = () => {
    InfoBox({
      cancelText: t('取消'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, getDefaultformData());
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
      title: t('确认重置表单内容'),
    });
  };

  /**
   * 变更业务选择
   */
  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
    formData.details.db_module_id = null;
    formData.details.nodes.backend = [];
  };

  // 获取 DM模块
  // watch(route.query, () => getModulesConfig(), {
  //   immediate: true,
  // });

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        return router.back();
      }
      router.push({
        name: String(route.query.from),
      });
    },
  });
</script>
<style lang="less" scoped>
  :deep(.domain-address) {
    display: flex;
    align-items: center;

    .bk-form-item {
      margin-bottom: 0;
    }
  }

  .choose-business {
    color: black;
  }

  .apply-sqlserver-instance {
    display: block;

    .apply-form-database {
      width: 435px;
      padding: 8px 12px;
      margin-top: 16px;
      font-size: 12px;
      background-color: #f5f7fa;
      border-radius: 2px;

      .apply-form-database-item {
        display: flex;
        line-height: 20px;

        .apply-form-database-label {
          width: 140px;
          text-align: right;
          flex-shrink: 0;
        }

        .apply-form-database-value {
          color: #313238;
          word-break: break-all;
        }
      }
    }

    .db-card {
      .spec-refresh-icon {
        margin-left: 8px;
        color: @primary-color;
        cursor: pointer;
      }

      & ~ .db-card {
        margin-top: 20px;
      }

      .bind-module {
        color: @primary-color;
        cursor: pointer;
      }
    }

    :deep(.item-input) {
      width: 435px;

      > .bk-radio-button {
        width: 50%;
      }
    }
  }

  .apply-dialog-quantity {
    margin-left: 15px;
    font-size: @font-size-normal;
    color: @default-color;
  }
</style>
