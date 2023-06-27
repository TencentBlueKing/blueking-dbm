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
  <SmartAction class="apply-influxdb">
    <DbForm
      ref="formRef"
      auto-label-width
      class="mb-16"
      :model="formdata"
      :rules="rules">
      <DbCard :title="$t('业务信息')">
        <BusinessItems
          v-model:app-abbr="formdata.details.db_app_abbr"
          v-model:biz-id="formdata.bk_biz_id"
          @change-biz="handleChangeBiz" />
        <GroupItem
          v-model="formdata.details.group_id"
          :biz-id="formdata.bk_biz_id"
          @change="handleChangeGroup" />
        <CloudItem
          v-model="formdata.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <!-- <RegionItem v-model="formdata.details.city_code" /> -->
      <DbCard :title="$t('部署需求')">
        <BkFormItem
          :label="$t('InfluxDB版本')"
          property="details.db_version"
          required>
          <BkSelect
            v-model="formdata.details.db_version"
            class="item-input"
            filterable
            :input-search="false"
            :loading="isDbVersionLoading">
            <BkOption
              v-for="item in dbVersionList"
              :key="item"
              :label="item"
              :value="item" />
          </BkSelect>
        </BkFormItem>
        <BkFormItem
          :label="$t('服务器选择')"
          property="details.ip_source"
          required>
          <BkRadioGroup
            v-model="formdata.details.ip_source">
            <BkRadioButton
              label="resource_pool"
              style="width: 218px;">
              {{ $t('自动从资源池匹配') }}
            </BkRadioButton>
            <BkRadioButton
              label="manual_input"
              style="width: 218px;">
              {{ $t('手动录入IP') }}
            </BkRadioButton>
          </BkRadioGroup>
        </BkFormItem>
        <Transition
          mode="out-in"
          name="dbm-fade">
          <BkFormItem
            v-if="formdata.details.ip_source === 'manual_input'"
            class="service-item"
            label=" "
            property="details.nodes.influxdb"
            required>
            <div>
              <IpSelector
                :biz-id="formdata.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formdata.details.nodes.influxdb"
                required
                style="display: inline-block;"
                @change="handleIpChange">
                <template #desc>
                  {{ $t('主机数数量即为实例数量_建议规格至少为2核4G') }}
                </template>
              </IpSelector>
            </div>
          </BkFormItem>
          <BkFormItem
            v-else
            :label="$t('InfluxDB实例')"
            required>
            <div class="resource-pool-item">
              <BkFormItem
                :label="$t('规格')"
                property="details.resource_spec.influxdb.spec_id"
                required>
                <SpecSelector
                  ref="specRef"
                  v-model="formdata.details.resource_spec.influxdb.spec_id"
                  cluster-type="influxdb"
                  machine-type="influxdb" />
              </BkFormItem>
              <BkFormItem
                :label="$t('数量')"
                property="details.resource_spec.influxdb.count"
                required>
                <BkInput
                  v-model="formdata.details.resource_spec.influxdb.count"
                  :min="1"
                  type="number" />
              </BkFormItem>
            </div>
          </BkFormItem>
        </Transition>
        <BkFormItem
          :label="$t('访问端口')"
          property="details.port"
          required>
          <BkInput
            v-model="formdata.details.port"
            clearable
            :min="1"
            style="width: 185px;"
            type="number" />
        </BkFormItem>
        <BkFormItem :label="$t('备注')">
          <BkInput
            v-model="formdata.remark"
            :maxlength="100"
            :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
            style="width: 655px;"
            type="textarea" />
        </BkFormItem>
      </DbCard>
    </DbForm>
    <template #action>
      <div>
        <BkButton
          :loading="baseState.isSubmitting"
          style="width: 88px;"
          theme="primary"
          @click="handleSubmit">
          {{ $t('提交') }}
        </BkButton>
        <BkButton
          class="ml8 w88"
          :disabled="baseState.isSubmitting"
          @click="handleReset">
          {{ $t('重置') }}
        </BkButton>
        <BkButton
          class="ml8 w88"
          :disabled="baseState.isSubmitting"
          @click="handleCancel">
          {{ $t('取消') }}
        </BkButton>
      </div>
    </template>
  </SmartAction>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { BizItem } from '@services/types/common';
  import type { HostDetails } from '@services/types/ip';
  import { getVersions } from '@services/versionFiles';

  import { useApplyBase, useInfo } from '@hooks';

  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  // import RegionItem from '@components/apply-items/RegionItem.vue';
  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import { getInitFormdata } from './common/base';
  import GroupItem from './components/GroupItem.vue';

  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });
  const groupName = ref('');
  const { t } = useI18n();
  const {
    baseState,
    bizState,
    handleCreateAppAbbr,
    handleCreateTicket,
    handleCancel,
  } = useApplyBase();

  const formdata = reactive(getInitFormdata());
  const formRef = ref();
  const specRef = ref();
  const rules = {
    'details.nodes.influxdb': [
      {
        required: true,
        validator: (value: Array<any>) => value.length >= 1,
        message: t('请添加服务器'),
        trigger: 'change',
      },
    ],
    'details.port': [
      {
        validator: (value: number) => value !== 8088,
        message: t('8088为服务内部占用端口'),
        trigger: 'blur',
      },
    ],
  };

  /**
   * 切换业务，需要重置 IP 相关的选择
   */
  function handleChangeBiz(info: BizItem) {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    formdata.details.group_id = '';
    formdata.details.nodes.influxdb = [];
  }
  /**
   * 变更所属管控区域
   */
  function handleChangeCloud(info: {id: number | string, name: string}) {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    formdata.details.nodes.influxdb = [];
  }

  function handleChangeGroup({ name }: {name: string}) {
    groupName.value = name;
  }

  /**
   * influxdb 版本处理
   */
  const isDbVersionLoading = ref(true);
  const dbVersionList = shallowRef<Array<string>>([]);
  getVersions({
    query_key: 'influxdb',
  }).then((data) => {
    dbVersionList.value = data;
  })
    .finally(() => {
      isDbVersionLoading.value = false;
    });

  // 更新 bookkeeper 节点
  const handleIpChange = (data: Array<HostDetails>) => {
    formdata.details.nodes.influxdb = data;
  };

  const handleSubmit = () => {
    formRef.value.validate()
      .then(() => {
        baseState.isSubmitting = true;

        const getDetails = () => {
          const details: Record<string, any> = {
            ...markRaw(formdata.details),
            group_name: groupName.value,
          };

          if (formdata.details.ip_source === 'resource_pool') {
            delete details.nodes;
            return {
              ...details,
              resource_spec: {
                influxdb: {
                  ...details.resource_spec.influxdb,
                  ...specRef.value.getData(),
                  count: Number(details.resource_spec.influxdb.count),
                },
              },
            };
          }

          delete details.resource_spec;
          return {
            ...details,
            nodes: {
              influxdb: formdata.details.nodes.influxdb.map(item => ({
                bk_host_id: item.host_id,
                ip: item.ip,
                bk_cloud_id: item.cloud_area.id,
                bk_biz_id: item.biz.id,
              })),
            },
          };
        };

        const params = {
          ...formdata,
          details: getDetails(),
        };

        // 若业务没有英文名称则先创建业务英文名称再创建单据，否则直接创建单据
        bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
      });
  };

  /**
   * 重置表单
   */
  const handleReset = () => {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formdata, getInitFormdata());
        formRef.value.clearValidate();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };
</script>

<style lang="less" scoped>
.apply-influxdb {
  display: block;

  .db-card {
    & ~ .db-card {
      margin-top: 20px;
    }
  }

  :deep(.item-input) {
    width: 435px;
  }

  .service-item {
    :deep(.bk-form-label) {
      &::after {
        content: "";
      }
    }
  }

  .input-desc {
    padding-left: 12px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;
  }

  .resource-pool-item {
    width: 655px;
    padding: 24px 0;
    background-color: #F5F7FA;
    border-radius: 2px;

    :deep(.bk-form-item) {
      .bk-form-label {
        width: 120px !important;
      }

      .bk-form-content {
        width: 314px;
        margin-left: 120px !important;
      }
    }
  }
}
</style>
