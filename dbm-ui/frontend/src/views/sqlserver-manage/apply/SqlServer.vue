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
            @change-biz="handleChangeBiz" />
          <BkFormItem
            ref="moduleRef"
            class="is-required"
            :description="t('表示DB的用途')"
            :label="t('DB模块名')"
            property="details.db_module_id"
            required>
            <BkSelect
              v-model="formData.details.db_module_id"
              class="item-input"
              :clearable="false"
              filterable
              :input-search="false"
              style="display: inline-block;">
              <BkOption
                v-for="item in moduleList"
                :key="item.db_module_id"
                :label="item.name"
                :value="item.db_module_id" />
              <template #extension>
                <p
                  v-bk-tooltips.top="{ content: t('请先选择所属业务') }"
                  class="ml-8">
                  <BkButton
                    class="create-module"
                    text
                    @click="handleCreateModule">
                    <DbIcon type="plus-circle" />
                    <span class="ml-4">{{ t('新建模块') }}</span>
                  </BkButton>
                </p>
              </template>
            </BkSelect>
            <DbIcon
              v-bk-tooltips="t('刷新获取最新DB模块名')"
              class="spec-refresh-icon ml-6"
              type="refresh"
              @click="getModulesConfig" />
            <div class="apply-form-database">
              <BkLoading :loading="isModuleLoading">
                <div v-if="levelConfigData && levelConfigData.conf_items.length">
                  <div
                    v-for="(item, index) in levelConfigData.conf_items"
                    :key="index"
                    class="apply-form-database-item">
                    <span class="apply-form-database-label">
                      {{ item.description || item.conf_name }}:
                    </span>
                    <span class="apply-form-database-value">
                      {{ item.conf_value }}
                    </span>
                  </div>
                </div>
                <div
                  v-else
                  class="no-items">
                  {{ t('该模块暂未绑定数据库相关配置') }}
                  <span
                    class="bind-module"
                    @click="handleBindConfig">
                    {{ isBindModule ? t('已完成') : t('去绑定') }}
                  </span>
                </div>
                <div
                  v-if="!levelConfigData?.conf_items.length"
                  class="bk-form-error mt-10">
                  {{ t('需要绑定数据库相关配置') }}
                </div>
              </BkLoading>
            </div>
          </BkFormItem>
          <CloudItem
            v-model="formData.details.bk_cloud_id"
            @change="handleChangeCloud" />
        </DbCard>
        <RegionItem
          ref="regionItemRef"
          v-model="formData.details.city_code" />
        <DbCard
          v-if="!isSingleType"
          :title="t('数据库部署信息')">
          <AffinityItem v-model="formData.details.disaster_tolerance_level" />
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
              type="number"
              @change="handleChangeClusterCount" />
          </BkFormItem>
          <BkFormItem
            :label="t('每组主机部署集群')"
            property="details.inst_num"
            required>
            <BkInput
              v-model="formData.details.inst_num"
              class="item-input"
              :max="maxInstNum"
              :min="1"
              type="number"
              @change="handleChangeInstCount" />
          </BkFormItem>
          <BkFormItem
            class="service"
            :label="t('域名设置')"
            required>
            <DomainTable
              v-model:domains="formData.details.domains"
              :form-data="formData"
              :is-sqlserver-single="isSingleType"
              :module-name="moduleName" />
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
              <BkRadioButton label="manual_input">
                {{ t('手动录入IP') }}
              </BkRadioButton>
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
                label="Master / Slave"
                property="details.nodes.backend"
                required>
                <IpSelector
                  :biz-id="formData.bk_biz_id"
                  :cloud-info="cloudInfo"
                  :data="formData.details.nodes.backend"
                  :disable-dialog-submit-method="backendHost"
                  @change="handleBackendIpChange">
                  <template #desc>
                    {{ t('需n台', { n: hostNums }) }}
                  </template>
                  <template #submitTips="{ hostList }">
                    <I18nT
                      keypath="需n台_已选n台"
                      style="font-size: 14px; color: #63656e;"
                      tag="span">
                      <span style="font-weight: bold; color: #2dcb56;">
                        {{ hostNums }}
                      </span>
                      <span style="font-weight: bold; color: #3a84ff;">
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
                property="details.resource_spec.backend.spec_id"
                required>
                <SpecSelector
                  ref="specBackendRef"
                  v-model="formData.details.resource_spec.backend.spec_id"
                  :biz-id="formData.bk_biz_id"
                  :cloud-id="formData.details.bk_cloud_id"
                  :cluster-type="clusterType"
                  :machine-type="clusterType"
                  style="width: 435px;" />
              </BkFormItem>
            </div>
          </Transition>
          <BkFormItem :label="t('备注')">
            <BkInput
              v-model="formData.remark"
              :maxlength="100"
              :placeholder="t('请提供更多有用信息申请信息_以获得更快审批')"
              style="width: 655px;"
              type="textarea" />
          </BkFormItem>
        </DbCard>
      </DbForm>
    </div>
    <template #action>
      <div>
        <BkButton
          class="w-88"
          :loading="isSubmitting"
          theme="primary"
          @click="handleSubmit">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          @click="() => isShowPreview = true">
          {{ t('预览') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          @click="handleResetFormdata">
          {{ t('重置') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88"
          @click="() => router.push({ name: String(route.query.from) })">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
  <!-- 预览功能 -->
  <BkDialog
    v-model:is-show="isShowPreview"
    header-position="left"
    :height="624"
    :width="1180">
    <template #header>
      {{ t('实例预览') }}
      <span class="apply-dialog-quantity">
        {{ t('共n条',{ n: formData.details.cluster_count }) }}
      </span>
    </template>
    <PreviewTable
      :data="previewData"
      :is-show-nodes="formData.details.ip_source === 'manual_input'"
      :is-single-type="isSingleType"
      :nodes="previewNodes" />
    <template #footer>
      <BkButton @click="() => isShowPreview = false">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getModules } from '@services/source/cmdb';
  import { getLevelConfig } from '@services/source/configs';
  import { createTicket } from '@services/source/ticket';
  import type { HostDetails } from '@services/types';

  import { useInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import {
    sqlServerType,
    type SqlServerTypeString,
  } from '@common/const';

  import AffinityItem from '@components/apply-items/AffinityItem.vue';
  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import RegionItem from '@components/apply-items/RegionItem.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import DomainTable from './components/DomainTable.vue';
  import PreviewTable from './components/PreviewTable.vue';

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const isSingleType = route.name === 'SqlServiceSingleApply';
  const clusterType = isSingleType ? 'sqlserver_single' : 'sqlserver_ha';

  const getDefaultformData = () => ({
    ticket_type: isSingleType ? 'SQLSERVER_SINGLE_APPLY' : 'SQLSERVER_HA_APPLY',
    remark: '',
    details: {
      db_app_abbr: '', // 业务 Code
      bk_cloud_id: 0,
      city_code: '',
      db_module_id: 0,
      cluster_count: 1,
      inst_num: 1,
      domains: [{ key: '' }],
      ip_source: 'resource_pool',
      nodes: {
        backend: [] as HostDetails[],
      },
      resource_spec: {
        backend: {
          spec_id: '',
          spec_name: '',
          spec_cluster_type: 'mysql',
          spec_machine_type: 'backend',
          affinity: '',
          location_spec: {
            city: '深圳', // 城市
            sub_zone_ids: [],
          },
          count: 0,
        },
      },
      start_mssql_port: 1000, // SQLServer起始端口
      disaster_tolerance_level: '', // 容灾
    },
    bk_biz_id: currentBizId,
  });

  const formRef = ref();
  const backendRef = ref();
  const moduleName = ref('');
  const moduleRef = ref();
  const isBindModule = ref(false);
  const isShowPreview = ref(false);
  const specBackendRef = ref();
  const dbVersion = ref();
  const charset = ref();
  const maxInstNum = ref();

  const cloudInfo = ref<{
    id: string | number,
    name: string
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
    'details.db_module_id': [
      {
        message: t('DB模块名不能为空'),
        trigger: 'blur',
        validator: (val: number) => !!val,
      },
    ],
    'details.nodes.backend': [{
      message: t('请添加服务器'),
      trigger: 'change',
      validator: () => formData.details.nodes.backend.length !== 0,
    }],
  }));

  const hostNums = computed(() => {
    const nums = Math.ceil(formData.details.cluster_count / formData.details.inst_num);
    return isSingleType ? nums : nums * 2;
  });

  /**
   * 预览功能
   */
  const previewNodes = computed(() => ({
    backend: formData.details.nodes.backend.map(host => ({
      ip: host.ip,
      bk_host_id: host.host_id,
      bk_cloud_id: host.cloud_id,
      bk_biz_id: host.biz.id,
    })),
  }));

  const tableData = computed(() => {
    if (moduleName.value && (formData.details.db_app_abbr)) {
      return formData.details.domains;
    }
    return [];
  });

  const previewData = computed(() => tableData.value.reduce((accumulator, { key }) => [...accumulator, {
    domain: `${moduleName.value}db.${key}.${formData.details.db_app_abbr}.db`,
    slaveDomain: `${moduleName.value}db.${key}.${formData.details.db_app_abbr}.db`,
    disasterDefence: t('同城跨园区'),
    deployStructure: isSingleType ? t('单节点部署') : t('主从部署'),
    version: dbVersion.value,
    charset: charset.value,
  }], [] as {
    domain:string,
    slaveDomain:string,
    disasterDefence:string,
    deployStructure:string,
    version:string,
    charset:string,
  }[]));

  /**
   * 获取模块详情
   */
  const {
    data: levelConfigData,
    run: fetchModulesDetails,
  } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess(result) {
      if (result.conf_items) {
        result.conf_items.forEach((item) => {
          if (item.conf_name === 'charset') {
            charset.value = item.conf_value;
          } else if (item.conf_name === 'db_version') {
            dbVersion.value = item.conf_value;
          }
        });
      }
    },
  });

  /**
   * 获取DB模块
   */
  const {
    data: moduleList,
    loading: isModuleLoading,
    run: fetchModulesConfig,
  } = useRequest(getModules, {
    manual: true,
    onSuccess(result) {
      if (result.length) {
        const module = result.find(item => item.db_module_id === formData.details.db_module_id);
        moduleName.value = module ? module.name : '';
      }
    },
  });

  /**
   * 创建表单
   */
  const {
    loading: isSubmitting,
    run: fetchCreatTicket,
  } = useRequest(createTicket, {
    manual: true,
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const backendHost = (hostList: Array<any>) => (hostList.length !== hostNums.value ? t('xx共需n台', { title: 'Master / Slave', n: hostNums.value }) : false);

  const handleChangeClusterCount = (value: number) => {
    if (formData.details.inst_num > value) {
      formData.details.inst_num = value;
      maxInstNum.value = value;
    }
  };

  const handleChangeInstCount = (value: number) => {
    if (value >= formData.details.cluster_count) {
      maxInstNum.value = formData.details.cluster_count;
    }
  };

  const getModulesConfig = () => {
    fetchModulesConfig({
      cluster_type: clusterType,
      bk_biz_id: Number(formData.bk_biz_id),
    });
  };

  /**
   * 新建模块
   */
  const handleCreateModule = () => {
    const url = router.resolve({
      name: 'SqlServerCreateDbModule',
      params: {
        type: formData.ticket_type,
        bk_biz_id: formData.bk_biz_id,
      },
      query: {
        from: String(route.name),
        cluster_type: clusterType,
        db_module_id: formData.details.db_module_id,
      },
    });
    window.open(url.href, '_blank');
  };

  /**
   * 变更所属管控区域
   */
  const handleChangeCloud = (info: {
    id: number | string,
    name: string
  }) => {
    cloudInfo.value = info;
    formData.details.nodes.backend = [];
  };

  /**
   * 更新 Backend
   */
  const handleBackendIpChange = (data: HostDetails[]) => {
    formData.details.nodes.backend = data;
    if (data.length > 0) {
      backendRef.value.clearValidate();
    }
  };

  /**
   * 提交申请
   */
  const handleSubmit = async () => {
    await formRef.value.validate();
    if (formData.details.ip_source === 'resource_pool') {
      const { spec_name: specName } = specBackendRef.value.getData();
      formData.details.resource_spec.backend.affinity = formData.details.disaster_tolerance_level;
      formData.details.resource_spec.backend.spec_name = specName;
      formData.details.resource_spec.backend.count =  hostNums.value;
    }
    fetchCreatTicket(formData);
  };

  /**
   * 重置表单
   */
  const handleResetFormdata = () => {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, getDefaultformData());
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };

  /**
   * 绑定数据库模块
   */
  const handleBindConfig = () => {
    if (isBindModule.value) {
      return;
    }
    const url = router.resolve({
      name: 'SelfServiceBindDbModule',
      params: {
        type: formData.ticket_type,
        bk_biz_id: formData.bk_biz_id,
        db_module_id: formData.details.db_module_id,
      },
    });
    window.open(url.href, '_blank');
  };

  /**
   * 变更业务选择
   */
  const handleChangeBiz = () => {
    formData.details.db_module_id = 0;
    formData.details.nodes.backend = [];
    moduleRef.value.clearValidate();
  };

  // 获取 DM模块
  watch(route.query, () => getModulesConfig(), {
    immediate: true,
  });

  // 根据DM模块 获取配置下拉展示详情
  watch(() => formData.details.db_module_id, (value) => {
    if (value) {
      fetchModulesDetails({
        bk_biz_id: Number(formData.bk_biz_id),
        meta_cluster_type: sqlServerType[formData.ticket_type as SqlServerTypeString].type,
        conf_type: 'deploy',
        level_value: value,
        level_name: 'module',
        version: 'deploy_info',
      });
    }
  });

  /**
   * 设置 domain 数量
   */
  watch(() => formData.details.cluster_count, (count: number) => {
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
  });

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

  .bk-form-item{
    margin-bottom: 0;
  }
}

.choose-business {
  color: black;
}

.apply-sqlserver-instance {
  display: block;

  .apply-form-database {
    width: 398px;
    padding:  8px 12px;
    margin-top: 16px;
    font-size: 12px;
    background-color: #f5f7fa;
    border-radius: 2px;
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

    >.bk-radio-button{
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
