<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction :offset-target="getSmartActionOffsetTarget">
    <div class="apply-instance">
      <DbForm
        ref="formRef"
        auto-label-width
        class="apply-form mb-16"
        :model="formData"
        :rules="rules">
        <DbCard :title="t('业务信息')">
          <BusinessItems
            v-model:app-abbr="formData.details.db_app_abbr"
            v-model:biz-id="formData.bk_biz_id"
            perrmision-action-id="redis_cluster_apply"
            @change-biz="handleChangeBiz" />
          <CloudItem
            v-model="formData.details.bk_cloud_id"
            @change="handleChangeCloud" />
        </DbCard>
        <RegionRequirementsOnlyCity
          v-if="isAppend"
          v-model="formData.details" />
        <RegionRequirementsCommon
          v-else
          ref="regionRequirements"
          v-model="formData.details" />
        <DbCard :title="t('数据库部署信息')">
          <BkFormItem
            :label="t('部署方式')"
            property="details.appendApply"
            required>
            <BkRadioGroup v-model="formData.details.appendApply">
              <BkRadio
                key="new"
                label="new">
                {{ t('全新主机部署') }}
              </BkRadio>
              <BkRadio
                key="append"
                label="append">
                {{ t('已有主从所在主机追加部署') }}
              </BkRadio>
            </BkRadioGroup>
          </BkFormItem>
        </DbCard>
        <DbCard :title="t('部署需求')">
          <BkFormItem
            v-if="!isAppend"
            :label="t('Redis 版本')"
            property="details.db_version"
            required>
            <DeployVersion
              v-model="formData.details.db_version"
              db-type="redis"
              query-key="redis" />
          </BkFormItem>
          <BkFormItem
            ref="clusterCountRef"
            :label="t('集群数量')"
            property="details.cluster_count"
            required>
            <BkInput
              v-model="formData.details.cluster_count"
              clearable
              :min="1"
              show-clear-only-hover
              style="width: 185px"
              type="number" />
          </BkFormItem>
          <BkFormItem
            v-if="!isAppend"
            ref="groupCountRef"
            :label="t('每组主机部署集群')"
            property="details.group_count"
            required>
            <BkInput
              v-model="formData.details.group_count"
              clearable
              :max="formData.details.cluster_count"
              :min="1"
              show-clear-only-hover
              style="width: 185px"
              type="number" />
          </BkFormItem>
          <BkFormItem
            v-if="!isAppend"
            :label="t('Redis 起始端口')"
            property="details.port"
            required>
            <BkInput
              v-model="formData.details.port"
              :max="65535"
              :min="1025"
              style="width: 185px"
              type="number" />
            <span class="apply-form__tips ml-10">{{
              t('按主机分配（集群实例），系统将从“起始端口”开始自动分配')
            }}</span>
          </BkFormItem>
          <BkFormItem
            :label="t('访问密码')"
            property="details.redis_pwd"
            required>
            <PasswordInput
              ref="passwordRef"
              v-model="formData.details.redis_pwd"
              :db-type="DBTypes.REDIS"
              @verify-result="verifyResult" />
          </BkFormItem>
          <BkFormItem
            v-if="!isAppend"
            :label="t('服务器选择')"
            property="details.ip_source"
            required>
            <BkRadioGroup
              v-model="formData.details.ip_source"
              class="item-input">
              <BkRadioButton
                key="resource_pool"
                label="resource_pool">
                {{ t('自动从资源池匹配') }}
              </BkRadioButton>
              <!-- 暂时去掉手动录入IP -->
              <!-- <BkRadioButton
                v-for="item of Object.values(redisIpSources)"
                :key="item.id"
                :label="item.id">
                {{ item.text }}
              </BkRadioButton> -->
            </BkRadioGroup>
          </BkFormItem>
          <BkFormItem
            v-if="!isAppend"
            :label="t('后端存储规格')"
            property="details.resource_spec.spec_id"
            required>
            <SpecSelector
              ref="specRef"
              v-model="formData.details.resource_spec.spec_id"
              :biz-id="formData.bk_biz_id"
              :city="formData.details.city_code"
              :cloud-id="formData.details.bk_cloud_id"
              :cluster-type="DBTypes.REDIS"
              :machine-type="MachineTypes.REDIS_TENDIS_CACHE"
              style="width: 314px" />
          </BkFormItem>
          <BkFormItem
            class="service"
            :label="t('域名设置')"
            required>
            <DomainTable
              v-model:domains="formData.details.infos"
              :app-abbr="formData.details.db_app_abbr"
              :biz-id="formData.bk_biz_id"
              :city-info="formData.details"
              :cloud-id="cloudInfo.id"
              :is-append="isAppend"
              :max-memory="maxMemory"
              :port="formData.details.port"
              :port-type="portType"
              @host-change="handleHostChange" />
          </BkFormItem>
          <EstimatedCost
            :params="{
              db_type: DBTypes.REDIS,
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
      <BkButton
        v-bk-tooltips="{
          content: t('密码不符合要求'),
          disabled: !Boolean(formData.details.redis_pwd) || passwordIsPass,
        }"
        class="w-88"
        :disabled="!passwordIsPass"
        :loading="baseState.isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
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
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { Form } from 'bkui-vue';
  import InfoBox from 'bkui-vue/lib/info-box';
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { type ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { getRedisMachineList } from '@services/source/redis';
  import { queryMachineInstancePair } from '@services/source/redisToolbox';
  import type { BizItem } from '@services/types';

  import { useApplyBase } from '@hooks';

  import { Affinity, ClusterTypes, DBTypes, MachineTypes, TicketTypes } from '@common/const';

  import DbForm from '@components/db-form/index.vue';

  import BusinessItems from '@views/db-manage/common/apply-items/BusinessItems.vue';
  import CloudItem from '@views/db-manage/common/apply-items/CloudItem.vue';
  import DeployVersion from '@views/db-manage/common/apply-items/DeployVersion.vue';
  import EstimatedCost from '@views/db-manage/common/apply-items/EstimatedCost.vue';
  import RegionRequirementsCommon from '@views/db-manage/common/apply-items/region-requirements/Common.vue';
  import RegionRequirementsOnlyCity from '@views/db-manage/common/apply-items/region-requirements/OnlyCity.vue';
  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';
  import PasswordInput from '@views/db-manage/common/password-input/Index.vue';

  import DomainTable, { type Domain } from './components/domain-table/Index.vue';

  const initData = () => ({
    bk_biz_id: '' as number | '',
    details: {
      appendApply: 'new', // 是否是追加部署
      bk_cloud_id: 0,
      city_code: '', // 追加就非必填
      city_name: '', // 非协议
      cluster_count: 1,
      cluster_type: ClusterTypes.REDIS_INSTANCE,
      db_app_abbr: '',
      db_version: '', // 追加就非必填
      disaster_tolerance_level: Affinity.SAME_SUBZONE_CROSS_SWTICH,
      group_count: 1,
      infos: [] as Domain[],
      ip_source: 'resource_pool',
      port: 30000, // 追加就非必填
      redis_pwd: '',
      resource_spec: {
        count: 2,
        spec_id: '',
      },
      sub_zone_ids: [] as number[],
    },
    remark: '',
    ticket_type: TicketTypes.REDIS_INS_APPLY,
  });

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { baseState, bizState, handleCancel, handleCreateAppAbbr, handleCreateTicket } = useApplyBase();

  const regionRequirementsRef = useTemplateRef('regionRequirements');

  const formRef = ref<InstanceType<typeof DbForm>>();
  const specRef = ref<InstanceType<typeof SpecSelector>>();
  const clusterCountRef = ref<InstanceType<typeof Form.FormItem>>();
  const groupCountRef = ref<InstanceType<typeof Form.FormItem>>();
  const cloudInfo = ref({
    id: '' as number | string,
    name: '',
  });
  const maxMemory = ref('0G');
  const passwordIsPass = ref(false);

  const formData = reactive(initData());

  const rules = {
    'details.cluster_count': [
      {
        message: t('集群数量 / 每组主机部署集群需为整数'),
        trigger: 'change',
        validator: (value: number) => {
          if (isAppend.value) {
            return true;
          }
          groupCountRef.value!.clearValidate();
          return value % formData.details.group_count === 0;
        },
      },
    ],
    'details.group_count': [
      {
        message: t('集群数量 / 每组主机部署集群需为整数'),
        trigger: 'change',
        validator: (value: number) => {
          clusterCountRef.value!.clearValidate();
          return formData.details.cluster_count % value === 0;
        },
      },
    ],
  };

  const isAppend = computed(() => formData.details.appendApply === 'append');
  const machineCount = computed(() => formData.details.cluster_count / formData.details.group_count);
  const portType = computed(() => {
    if (formData.details.cluster_count % formData.details.group_count !== 0) {
      return '';
    }
    if (formData.details.cluster_count === formData.details.group_count) {
      return 'increment'; // 递增端口号
    }
    if (formData.details.group_count === 1) {
      return 'same'; // 端口号相同
    }
    const ports = Array(formData.details.group_count)
      .fill(0)
      .map((_, index) => formData.details.port + index);
    const groups = formData.details.cluster_count / formData.details.group_count;
    return _.flatMap(
      Array(groups)
        .fill(0)
        .map(() => ports),
    );
  });

  const resourceSepc = computed(
    () =>
      ({
        backend_group: {
          count: machineCount.value,
          spec_id: formData.details.resource_spec.spec_id,
        },
      }) as ComponentProps<typeof EstimatedCost>['params']['resource_spec'],
  );

  watch(
    [() => formData.details.resource_spec.spec_id, machineCount],
    ([newSpecId]) => {
      nextTick(() => {
        if (newSpecId) {
          const { mem } = specRef.value!.getData();
          const capicity = ((mem?.min ?? 0) * 0.9 * machineCount.value) / formData.details.cluster_count;
          maxMemory.value = `${capicity.toFixed(2)}G`;
        } else {
          maxMemory.value = '0G';
        }
      });
    },
    {
      deep: true,
    },
  );

  // 设置 domain 数量
  watch(
    () => formData.details.cluster_count,
    (count) => {
      if (count > 0 && count <= 200) {
        const len = formData.details.infos.length;
        if (count > len) {
          const appends = Array.from({ length: count - len }, () => ({
            cluster_name: '',
            databases: 2,
            masterHost: {
              bk_cloud_id: 0,
              bk_host_id: 0,
              ip: '',
            },
            slaveHost: {
              bk_cloud_id: 0,
              bk_host_id: 0,
              ip: '',
            },
          }));
          formData.details.infos.push(...appends);
          return;
        }
        if (count < len) {
          formData.details.infos.splice(count, len - count);
          return;
        }
      }
    },
    {
      immediate: true,
    },
  );

  const verifyResult = (isPass: boolean) => {
    passwordIsPass.value = isPass;
  };

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  const handleChangeBiz = (info: BizItem) => {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;
  };

  const handleChangeCloud = (info: { id: number | string; name: string }) => {
    cloudInfo.value = info;
  };

  const handleHostChange = async (filedName: string, value: string, index: number) => {
    await formRef.value!.validate(filedName);
    getRedisMachineList({
      bk_city_name: formData.details.city_name,
      bk_cloud_id: formData.details.bk_cloud_id,
      cluster_type: ClusterTypes.REDIS_INSTANCE,
      instance_role: 'redis_master',
      ip: value,
    }).then((data) => {
      const redisMachineList = data.results;
      if (redisMachineList.length) {
        const [redisMachineItem] = redisMachineList;
        Object.assign(formData.details.infos[index], {
          masterHost: {
            bk_cloud_id: redisMachineItem.bk_cloud_id,
            bk_host_id: redisMachineItem.bk_host_id,
            ip: value,
          },
        });

        const ipInfo = `${formData.details.bk_cloud_id}:${value}`;
        queryMachineInstancePair({ machines: [ipInfo] }).then((pairResult) => {
          const ipMap = pairResult.machines!;
          if (ipMap[ipInfo]) {
            Object.assign(formData.details.infos[index], {
              slaveHost: {
                bk_cloud_id: ipMap[ipInfo].bk_cloud_id,
                bk_host_id: ipMap[ipInfo].bk_host_id,
                ip: ipMap[ipInfo].ip,
              },
            });
          }
        });
      }
    });
  };

  const handleResetFormdata = () => {
    InfoBox({
      cancelText: t('取消'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, initData());
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
      title: t('确认重置表单内容'),
    });
  };

  const handleSubmit = async () => {
    await formRef.value!.validate();

    baseState.isSubmitting = true;

    const getDetails = () => {
      const { details }: { details: Partial<UnwrapRef<typeof formData>['details']> } = _.cloneDeep(formData);

      if (details.appendApply === 'new') {
        Object.assign(details, {
          infos: details.infos!.map((infoItem) => ({
            cluster_name: infoItem.cluster_name,
            databases: infoItem.databases,
          })),
          resource_spec: {
            backend_group: {
              count: Math.ceil(machineCount.value),
              spec_id: details.resource_spec!.spec_id,
              ...specRef.value!.getData(),
              ...regionRequirementsRef.value!.getValue(),
            },
          },
        });
      } else {
        delete details.port;
        delete details.city_code;
        delete details.db_version;
        delete details.resource_spec;

        Object.assign(details, {
          infos: details.infos!.map((infoItem) => ({
            backend_group: {
              master: infoItem.masterHost,
              slave: infoItem.slaveHost,
            },
            cluster_name: infoItem.cluster_name,
            databases: infoItem.databases,
          })),
        });
      }

      delete details.cluster_count;
      delete details.group_count;
      delete details.appendApply;
      delete details.city_name;

      return {
        ...details,
        append_apply: isAppend.value,
        ip_source: isAppend.value ? 'manual_input' : 'resource_pool',
      };
    };

    const params = {
      ...formData,
      details: getDetails(),
    };

    // 若业务没有英文名称则先创建业务英文名称再创建单据，反正直接创建单据
    bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
  };

  defineExpose({
    routerBack() {
      if (!route.query.from) {
        router.back();
        return;
      }
      router.push({
        name: route.query.from as string,
      });
    },
  });
</script>

<style lang="less" scoped>
  @import '@styles/applyInstance.less';

  .apply-instance {
    :deep(.item-input) {
      width: 435px;
    }

    .input-desc {
      margin-left: 12px;
      font-size: 12px;
      color: #63656e;
    }

    :deep(.password-form-item) {
      width: 435px;
    }

    .resource-pool-item {
      width: 655px;
      padding: 24px 0;
      background-color: #f5f7fa;
      border-radius: 2px;

      .bk-form-item {
        .bk-form-label {
          width: 120px !important;
        }

        .bk-form-content {
          margin-left: 120px !important;

          .bk-select,
          .bk-input {
            width: 314px;
          }
        }
      }
    }
  }
</style>
