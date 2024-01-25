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
            v-model:biz-id="formData.bk_biz_id" />
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
                v-for="(item) in moduleList"
                :key="item.db_module_id"
                :label="item.name"
                :value="item.db_module_id" />
              <template #extension>
                <p
                  v-bk-tooltips.top="{
                    content: t('请先选择所属业务'),
                  }">
                  <BkButton
                    class="create-module"
                    text
                    @click="handleCreateModule">
                    <i
                      class="db-icon-plus-circle" />
                    {{ t('新建模块') }}
                  </BkButton>
                </p>
              </template>
            </BkSelect>
            <span
              v-bk-tooltips.top="t('刷新获取最新DB模块名')"
              class="refresh-module"
              @click="getModulesConfig">
              <i class="db-icon-refresh" />
            </span>
            <div
              class="apply-form-database">
              <BkLoading :loading="isModuleLoading">
                <div>
                  <div
                    v-for="(item, index) in levelConfigData?.conf_items"
                    :key="index"
                    class="apply-form-database-item">
                    <span class="apply-form-database-label">{{ item.description || item.conf_name }}:</span>
                    <span class="apply-form-database-value">{{ item.conf_value }}</span>
                  </div>
                </div>
                <div
                  class="no-items">
                  {{ t('该模块暂未绑定数据库相关配置') }}
                  <span
                    class="bind-module">{{ t('已完成去绑定') }}</span>
                </div>
                <div
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
          ref="regionItemRef" />
        <DbCard
          v-if="!isSingleType"
          :title="t('数据库部署信息')">
          <AffinityItem />
          <BkFormItem
            :label="t('SQLServer起始端口')"
            property="details.start_sqlserver_port"
            required>
            <BkInput
              v-model="formData.details.start_sqlserver_port"
              class="item-input"
              :max="65535"
              :min="1025"
              type="number" />
            <span class="ml-10">{{ t('默认从起始端口开始分配') }}</span>
          </BkFormItem>
        </DbCard>
        <DbCard :title="t('需求信息')">
          <BkFormItem
            label="集群数量"
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
            label="每组主机部署集群"
            property="details.inst_num"
            required>
            <BkInput
              v-model="formData.details.inst_num"
              class="item-input"
              :min="1"
              type="number" />
          </BkFormItem>
          <BkFormItem
            class="service"
            :label="t('域名设置')"
            required>
            <DomainTable
              v-model:domains="formData.details.domains"
              :formdata="formData"
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
                      <span style="font-weight: bold; color: #2dcb56;">  {{ hostNums }} </span>
                      <span style="font-weight: bold; color: #3a84ff;">  {{ hostList.length }} </span>
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
                property="details.resource_spec.spec_id"
                required>
                <SpecSelector
                  ref="specBackendRef"
                  v-model="formData.details.resource_spec.spec_id"
                  :biz-id="formData.bk_biz_id"
                  :cloud-id="formData.details.bk_cloud_id"
                  :cluster-type="ClusterTypes.SQLSERVER_SINGLE"
                  machine-type="backend"
                  style="width: 435px;" />
              </BkFormItem>
            </div>
          </Transition>
          <BkFormItem :label="t('备注')">
            <BkInput
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
          theme="primary">
          {{ t('提交') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88">
          {{ t('预览') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88">
          {{ t('重置') }}
        </BkButton>
        <BkButton
          class="ml-8 w-88">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
  <!-- 预览功能 -->
  <BkDialog
    header-position="left"
    :height="624"
    :width="1180">
    <template #header>
      {{ t('实例预览') }}
      <span>{{ t('共n条') }}</span>
    </template>
    <template #footer>
      <BkButton>
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
  import type { HostDetails } from '@services/types';

  import {
    ClusterTypes,
    sqlserverType,
    type SQLserverTypeString,
    TicketTypes,
  } from '@common/const';

  import AffinityItem from '@components/apply-items/AffinityItem.vue';
  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import RegionItem from '@components/apply-items/RegionItem.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import DomainTable from './components/DomainTable.vue';

  const { t } = useI18n();

  const route = useRoute();
  const router = useRouter();

  const isSingleType = route.name === 'SqlServiceApplySingle';

  const getDefaultformData = () => ({
    bk_biz_id: '' as number | '',
    remark: '',
    ticket_type: isSingleType ? TicketTypes.SQLSERVER_SINGLE_APPLY : TicketTypes.SQLSERVER_HA_APPLY,
    details: {
      bk_cloud_id: 0,
      city_code: '',
      db_app_abbr: '',
      spec: '',
      db_module_id: 0,
      cluster_count: 1,
      inst_num: 1,
      start_sqlserver_port: 20000,
      domains: [{ key: '' }],
      ip_source: 'resource_pool', // 服务器选择 资源池
      nodes: {
        backend: [] as HostDetails[],
      },
      resource_spec: {
        count: 0,
        spec_id: '',
        location_spec: {
          city: '',
          sub_zone_ids: [],
        },
      },
    },
  });

  const backendRef = ref();

  const formData = reactive(getDefaultformData());

  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });

  const rules = computed(() => ({
    'details.db_app_abbr': [
      {
        message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
        trigger: 'blur',

      },
    ],
    'details.db_module_id': [
      {
        message: t('请先选择所属业务'),
        trigger: 'blur',
        validator: () => !!formData.bk_biz_id,
      },
      {
        message: t('DB模块名不能为空'),
        trigger: 'blur',
        validator: (val: number) => !!val,
      },
    ],
    'details.nodes.backend': [{
      message: t('请添加服务器'),
      trigger: 'change',
      validator: () => {
        const counts = formData.details.nodes.backend.length;
        return counts !== 0;
      },
    }],
  }));

  const moduleName = computed(() => {
    const module = moduleList.find(item => item.db_module_id === formData.details.db_module_id);
    return module ? module.name : '';
  });

  const hostNums = computed(() => {
    const { cluster_count: clusterCount, inst_num: instCount } = formData.details;
    if (clusterCount <= 0 || instCount <= 0) {
      return 0;
    }
    const nums = Math.ceil(clusterCount / instCount);
    return isSingleType ? nums : nums * 2;
  });

  /**
   * 获取模块详情
   */
  const {
    data: levelConfigData,
    run: fetchModulesDetails,
  } = useRequest(getLevelConfig, {
    manual: true,
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
  });

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const backendHost = (hostList: Array<any>) => (hostList.length !== hostNums.value ? t('xx共需n台', { title: 'Master / Slave', n: hostNums.value }) : false);

  const handleChangeClusterCount = (value: number) => {
    if (formData.details.inst_num > value) {
      formData.details.inst_num = value;
    }
  };

  const getModulesConfig = () => {
    fetchModulesConfig({
      cluster_type: isSingleType ? 'sqlserver_single' : 'sqlserver_ha',
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
        db_module_id: formData.details.db_module_id,
      },
      query: {
        from: String(route.name),
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
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;
    formData.details.nodes.backend = [];
  };

  /**
   * 更新 Backend
   */
  const handleBackendIpChange = (data: HostDetails[]) => {
    formData.details.nodes.backend = [...data];
    if (formData.details.nodes.backend.length > 0) {
      backendRef.value.clearValidate();
    }
  };

  // 获取 DM模块
  watch(() => route.query, ({ bizId }) => {
    formData.bk_biz_id = Number(bizId);
    getModulesConfig();
  }, {
    immediate: true,
  });

  // 根据DM模块 获取配置下拉展示详情
  watch(() => formData.details.db_module_id, (value) => {
    if (value) {
      fetchModulesDetails({
        bk_biz_id: Number(route.query.bizId),
        meta_cluster_type: sqlserverType[formData.ticket_type as SQLserverTypeString].type,
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
    if (count > 0 && count <= 200) {
      const len = formData.details.domains.length;
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
    & ~ .db-card {
      margin-top: 20px;
    }
  }

  :deep(.item-input) {
    width: 435px;

    >.bk-radio-button{
      width: 50%;
    }
  }

}
</style>
