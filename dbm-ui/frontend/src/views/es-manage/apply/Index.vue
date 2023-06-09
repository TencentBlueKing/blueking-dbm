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
  <SmartAction
    class="apply-es-page"
    :offset-target="getSmartActionOffsetTarget">
    <DbForm
      ref="formRef"
      auto-label-width
      :model="formData"
      :rules="rules"
      style="margin-bottom: 16px;">
      <DbCard :title="$t('业务信息')">
        <BusinessItems
          v-model:app-abbr="formData.details.db_app_abbr"
          v-model:biz-id="formData.bk_biz_id"
          @change-biz="handleChangeBiz" />
        <ClusterName v-model="formData.details.cluster_name" />
        <ClusterAlias v-model="formData.details.cluster_alias" />
        <CloudItem
          v-model="formData.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <!-- <RegionItem
        v-model="formData.details.city_code" /> -->
      <DbCard :title="$t('部署需求')">
        <BkFormItem
          :label="$t('ES版本')"
          property="details.db_version"
          required>
          <BkSelect
            v-model="formData.details.db_version"
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
            v-model="formData.details.ip_source">
            <BkRadioButton
              v-bk-tooltips="$t('该功能暂未开放')"
              disabled
              label="auto"
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
        <template v-if="formData.details.ip_source === 'manual_input'">
          <DbFormItem
            :label="$t('Master节点')"
            property="details.nodes.master"
            required>
            <div>
              <IpSelector
                :biz-id="formData.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formData.details.nodes.master"
                :disable-dialog-submit-method="masterDisableDialogSubmitMethod"
                :disable-host-method="masterDisableHostMethod"
                required
                :show-view="false"
                style="display: inline-block;"
                @change="handleMasterIpListChange">
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="至少n台_已选n台"
                    style="font-size: 14px; color: #63656e;"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56;"> 3 </span>
                    <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
                <template #desc>
                  {{ $t('至少3台_且为奇数_建议规格至少2核4G') }}
                </template>
              </IpSelector>
            </div>
            <RenderHostTable
              v-model:data="formData.details.nodes.master"
              :biz-id="formData.bk_biz_id" />
          </DbFormItem>
          <DbFormItem
            :label="$t('Client节点')"
            property="details.nodes.client"
            required>
            <IpSelector
              :biz-id="formData.bk_biz_id"
              :cloud-info="cloudInfo"
              :data="formData.details.nodes.client"
              :disable-host-method="clientDisableHostMethod"
              required
              :show-view="false"
              @change="handleClientIpListChange">
              <template #desc>
                {{ $t('至少1台_建议规格至少2核4G') }}
              </template>
            </IpSelector>
            <RenderHostTable
              v-model:data="formData.details.nodes.client"
              :biz-id="formData.bk_biz_id" />
          </DbFormItem>
          <DbFormItem
            :label="$t('热节点')"
            property="details.nodes.hot"
            required>
            <IpSelector
              :biz-id="formData.bk_biz_id"
              :cloud-info="cloudInfo"
              :data="formData.details.nodes.hot"
              :disable-host-method="hotDisableHostMethod"
              required
              :show-view="false"
              @change="handleHotIpListChange">
              <template #desc>
                {{ $t('至少1台_建议规格至少2核4G') }}
              </template>
            </IpSelector>
            <WithInstanceHostTable
              v-model:data="formData.details.nodes.hot"
              :biz-id="formData.bk_biz_id" />
          </DbFormItem>
          <DbFormItem
            :label="$t('冷节点')"
            property="details.nodes.cold"
            required>
            <IpSelector
              :biz-id="formData.bk_biz_id"
              :cloud-info="cloudInfo"
              :data="formData.details.nodes.cold"
              :disable-host-method="coldDisableHostMethod"
              required
              :show-view="false"
              @change="handleColdIpListChange">
              <template #desc>
                {{ $t('至少1台_建议规格至少2核4G') }}
              </template>
            </IpSelector>
            <WithInstanceHostTable
              v-model:data="formData.details.nodes.cold"
              :biz-id="formData.bk_biz_id" />
          </DbFormItem>
          <BkFormItem
            :label="$t('访问端口')"
            property="details.http_port"
            required>
            <BkInput
              v-model="formData.details.http_port"
              clearable
              :min="1"
              show-clear-only-hover
              style="width: 185px;"
              type="number" />
          </BkFormItem>
        </template>
        <BkFormItem :label="$t('备注')">
          <BkInput
            v-model="formData.remark"
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
  import {
    reactive,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { BizItem } from '@services/types/common';
  import type {
    HostDetails,
  } from '@services/types/ip';
  import { getVersions } from '@services/versionFiles';

  import { useApplyBase, useInfo  } from '@hooks';

  import BusinessItems from '@components/apply-items/BusinessItems.vue';
  import CloudItem from '@components/apply-items/CloudItem.vue';
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  import WithInstanceHostTable, {
    type IHostTableDataWithInstance,
  } from '@components/cluster-common/big-data-host-table/es-host-table/index.vue';
  import RenderHostTable, {
    type IHostTableData,
  } from '@components/cluster-common/big-data-host-table/RenderHostTable.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  const { t } = useI18n();

  const makeMapByHostId = (hostList: Array<HostDetails>) =>  hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  const genDefaultFormData = () => ({
    bk_biz_id: '' as number | '',
    remark: '',
    ticket_type: 'ES_APPLY',
    details: {
      bk_cloud_id: '',
      db_app_abbr: '',
      cluster_name: '',
      cluster_alias: '',
      city_code: '',
      db_version: '',
      ip_source: 'manual_input',
      nodes: {
        master: [] as Array<IHostTableData>,
        client: [] as Array<IHostTableData>,
        hot: [] as Array<IHostTableDataWithInstance>,
        cold: [] as Array<IHostTableDataWithInstance>,
      },
      http_port: 9200,
    },
  });

  const formatIpDataWidthInstance = (data: Array<HostDetails>) => data.map(item => ({
    instance_num: 1,
    ...item,
  }));


  const formRef = ref();
  const formData = reactive(genDefaultFormData());

  const isDbVersionLoading = ref(true);
  const dbVersionList = shallowRef<Array<string>>([]);
  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });

  const rules = {
    'details.nodes.master': [
      {
        validator: (value: Array<any>) => value.length >= 3 && value.length % 2 === 1,
        message: t('Master节点数至少为3台_且为奇数'),
        trigger: 'change',
      },
    ],
    'details.nodes.client': [
      {
        validator: (value: Array<any>) => value.length > 0,
        message: t('Client节点数不能为空'),
        trigger: 'change',
      },
    ],
    'details.nodes.hot': [
      {
        validator: (value: Array<any>) => value.length > 0,
        message: t('热节点不能为空'),
        trigger: 'change',
      },
    ],
    'details.nodes.cold': [
      {
        validator: (value: Array<any>) => value.length > 0,
        message: t('冷节点不能为空'),
        trigger: 'change',
      },
    ],
  };

  const getSmartActionOffsetTarget = () => document.querySelector('.bk-form-content');

  // 获取 DB 版本列表
  getVersions({
    query_key: 'es',
  }).then((data) => {
    dbVersionList.value = data;
  })
    .finally(() => {
      isDbVersionLoading.value = false;
    });

  const {
    baseState,
    bizState,
    handleCreateAppAbbr,
    handleCreateTicket,
    handleCancel,
  } = useApplyBase();

  // 切换业务，需要重置 IP 相关的选择
  function handleChangeBiz(info: BizItem) {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    formData.details.nodes.hot = [];
    formData.details.nodes.cold = [];
    formData.details.nodes.client = [];
    formData.details.nodes.master = [];
  }

  /**
   * 变更所属管控区域
   */
  function handleChangeCloud(info: {id: number | string, name: string}) {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    formData.details.nodes.hot = [];
    formData.details.nodes.cold = [];
    formData.details.nodes.client = [];
    formData.details.nodes.master = [];
  }

  // master、client、热节点、冷节点互斥
  const masterDisableHostMethod = (data: any) => {
    const clientHostMap = makeMapByHostId(formData.details.nodes.client);
    if (clientHostMap[data.host_id]) {
      return t('主机已被client节点使用');
    }
    const hotHostMap = makeMapByHostId(formData.details.nodes.hot);
    if (hotHostMap[data.host_id]) {
      return t('主机已被热节点使用');
    }
    const coldHostMap = makeMapByHostId(formData.details.nodes.cold);
    if (coldHostMap[data.host_id]) {
      return t('主机已被冷节点使用');
    }

    return false;
  };

  // master、client、热节点、冷节点互斥
  const clientDisableHostMethod = (data: any) => {
    const masterHostMap = makeMapByHostId(formData.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master节点使用');
    }
    const hotHostMap = makeMapByHostId(formData.details.nodes.hot);
    if (hotHostMap[data.host_id]) {
      return t('主机已被热节点使用');
    }
    const coldHostMap = makeMapByHostId(formData.details.nodes.cold);
    if (coldHostMap[data.host_id]) {
      return t('主机已被冷节点使用');
    }

    return false;
  };

  // master、client、热节点、冷节点互斥
  const hotDisableHostMethod = (data: any) => {
    const masterHostMap = makeMapByHostId(formData.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master节点使用');
    }
    const clientHostMap = makeMapByHostId(formData.details.nodes.client);
    if (clientHostMap[data.host_id]) {
      return t('主机已被client节点使用');
    }
    const coldHostMap = makeMapByHostId(formData.details.nodes.cold);
    if (coldHostMap[data.host_id]) {
      return t('主机已被冷节点使用');
    }

    return false;
  };

  // master、client、热节点、冷节点互斥
  const coldDisableHostMethod = (data: any) => {
    const masterHostMap = makeMapByHostId(formData.details.nodes.master);
    if (masterHostMap[data.host_id]) {
      return t('主机已被Master节点使用');
    }
    const clientHostMap = makeMapByHostId(formData.details.nodes.client);
    if (clientHostMap[data.host_id]) {
      return t('主机已被client节点使用');
    }
    const hotHostMap = makeMapByHostId(formData.details.nodes.hot);
    if (hotHostMap[data.host_id]) {
      return t('主机已被热节点使用');
    }
    return false;
  };

  // master 节点 IP 选择器提交
  const masterDisableDialogSubmitMethod = (hostList: Array<any>) => (hostList.length >= 3 ? false : t('至少n台', { n: 3 }));
  // 更新 master 节点
  const handleMasterIpListChange = (data: Array<HostDetails>) => {
    formData.details.nodes.master = data;
  };
  // 更新 client 节点IP
  const handleClientIpListChange = (data: Array<HostDetails>) => {
    formData.details.nodes.client = data;
  };
  // 更新热节点IP
  const handleHotIpListChange = (data: Array<HostDetails>) => {
    formData.details.nodes.hot = formatIpDataWidthInstance(data);
  };
  // 更新冷节点IP
  const handleColdIpListChange = (data: Array<HostDetails>) => {
    formData.details.nodes.cold = formatIpDataWidthInstance(data);
  };

  // 提交
  const handleSubmit = () => {
    formRef.value.validate()
      .then(() => {
        baseState.isSubmitting = true;
        const mapIpField = (ipList: Array<IHostTableData>) => ipList.map(item => ({
          bk_host_id: item.host_id,
          ip: item.ip,
          bk_cloud_id: item.cloud_area.id,
          bk_biz_id: item.biz.id,
        }));
        const mapIpFieldWithInstance = (ipList: Array<IHostTableDataWithInstance>) => ipList.map(item => ({
          bk_host_id: item.host_id,
          ip: item.ip,
          bk_cloud_id: item.cloud_area.id,
          instance_num: item.instance_num,
          bk_biz_id: item.biz.id,
        }));

        const params = {
          ...formData,
          details: {
            ...formData.details,
            nodes: {
              master: mapIpField(formData.details.nodes.master),
              client: mapIpField(formData.details.nodes.client),
              hot: mapIpFieldWithInstance(formData.details.nodes.hot),
              cold: mapIpFieldWithInstance(formData.details.nodes.cold),
            },
          },
        };

        // 若业务没有英文名称则先创建业务英文名称再创建单据，否则直接创建单据
        bizState.hasEnglishName ? handleCreateTicket(params) : handleCreateAppAbbr(params);
      });
  };

  // 重置表单
  const handleReset = () => {
    useInfo({
      title: t('确认重置表单内容'),
      content: t('重置后_将会清空当前填写的内容'),
      onConfirm: () => {
        Object.assign(formData, genDefaultFormData());
        formRef.value.clearValidate();
        nextTick(() => {
          window.changeConfirm = false;
        });
        return true;
      },
    });
  };
</script>
<style lang="less">
  .apply-es-page {
    display: block;

    .db-card {
      & ~ .db-card {
        margin-top: 20px;
      }
    }

    .item-input {
      width: 435px;
    }

    .input-desc {
      padding-left: 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }
  }
</style>
