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
  <SmartAction class="apply-pulsar">
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
        <ClusterName v-model="formdata.details.cluster_name" />
        <ClusterAlias v-model="formdata.details.cluster_alias" />
        <CloudItem
          v-model="formdata.details.bk_cloud_id"
          @change="handleChangeCloud" />
      </DbCard>
      <!-- <RegionItem v-model="formdata.details.city_code" /> -->
      <DbCard :title="$t('部署需求')">
        <BkFormItem
          :label="$t('Pulsar版本')"
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
        <template v-if="formdata.details.ip_source === 'manual_input'">
          <BkFormItem
            :label="$t('Bookkeeper节点')"
            property="details.nodes.bookkeeper"
            required>
            <div>
              <IpSelector
                :biz-id="formdata.bk_biz_id"
                :cloud-info="cloudInfo"
                :data="formdata.details.nodes.bookkeeper"
                :disable-dialog-submit-method="ipSelectorDisabledSubmitMethods.bookkeeper"
                :disable-host-method="bookkeeperDisableHostMethod"
                required
                style="display: inline-block;"
                @change="handleBookkeeperIpListChange">
                <template #submitTips="{ hostList }">
                  <I18nT
                    keypath="至少n台_已选n台"
                    style="font-size: 14px; color: #63656e;"
                    tag="span">
                    <span style="font-weight: bold; color: #2dcb56;"> 2 </span>
                    <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                  </I18nT>
                </template>
                <template #desc>
                  {{ $t('至少2台_建议规格至少为2核4G') }}
                </template>
              </IpSelector>
            </div>
          </BkFormItem>
          <BkFormItem
            :label="$t('Zookeeper节点')"
            property="details.nodes.zookeeper"
            required>
            <IpSelector
              :biz-id="formdata.bk_biz_id"
              :cloud-info="cloudInfo"
              :data="formdata.details.nodes.zookeeper"
              :disable-dialog-submit-method="ipSelectorDisabledSubmitMethods.zookeeper"
              :disable-host-method="zookeeperDisableHostMethod"
              required
              @change="handleZookeeperIpListChange">
              <template #submitTips="{ hostList }">
                <I18nT
                  keypath="需n台_已选n台"
                  style="font-size: 14px; color: #63656e;"
                  tag="span">
                  <span style="font-weight: bold; color: #2dcb56;"> 3 </span>
                  <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                </I18nT>
              </template>
              <template #desc>
                {{ $t('需3台_建议规格至少为2核4G') }}
              </template>
            </IpSelector>
          </BkFormItem>
          <BkFormItem
            :label="$t('Broker节点')"
            property="details.nodes.broker"
            required>
            <IpSelector
              :biz-id="formdata.bk_biz_id"
              :cloud-info="cloudInfo"
              :data="formdata.details.nodes.broker"
              :disable-dialog-submit-method="ipSelectorDisabledSubmitMethods.broker"
              :disable-host-method="brokerDisableHostMethod"
              required
              @change="handleBrokerIpListChange">
              <template #submitTips="{ hostList }">
                <I18nT
                  keypath="至少n台_已选n台"
                  style="font-size: 14px; color: #63656e;"
                  tag="span">
                  <span style="font-weight: bold; color: #2dcb56;"> 1 </span>
                  <span style="font-weight: bold; color: #3a84ff;"> {{ hostList.length }} </span>
                </I18nT>
              </template>
              <template #desc>
                {{ $t('至少1台_建议规格至少为2核4G') }}
              </template>
            </IpSelector>
          </BkFormItem>
          <BkFormItem
            :label="$t('Partition数量')"
            property="details.partition_num"
            required>
            <BkInput
              v-model="formdata.details.partition_num"
              clearable
              :min="1"
              style="width: 185px;"
              type="number" />
          </BkFormItem>
          <BkFormItem
            :label="$t('消息保留')"
            property="details.retention_hours"
            required>
            <BkInput
              v-model="formdata.details.retention_hours"
              clearable
              :min="1"
              style="width: 185px;"
              type="number" />
            <span class="input-desc">{{ $t('小时') }}</span>
          </BkFormItem>
          <BkFormItem
            :label="$t('副本数量')"
            property="details.replication_num"
            required>
            <BkInput
              v-model="formdata.details.replication_num"
              clearable
              :max="formdata.details.nodes.bookkeeper.length || 2"
              :min="2"
              style="width: 185px;"
              type="number" />
            <span class="input-desc">{{ $t('至少2_不能超过Bookkeeper数量') }}</span>
          </BkFormItem>
          <BkFormItem
            :label="$t('至少写入成功副本数量')"
            property="details.ack_quorum"
            required>
            <BkInput
              v-model="formdata.details.ack_quorum"
              clearable
              :max="formdata.details.replication_num || 2"
              :min="1"
              style="width: 185px;"
              type="number" />
            <span class="input-desc">{{ $t('当达到数量后_立即返回结果_减少用户等待时间') }}</span>
          </BkFormItem>
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
        </template>
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
  import ClusterAlias from '@components/apply-items/ClusterAlias.vue';
  import ClusterName from '@components/apply-items/ClusterName.vue';
  // import RegionItem from '@components/apply-items/RegionItem.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import { getInitFormdata } from './common/base';

  const { t } = useI18n();
  const {
    baseState,
    bizState,
    handleCreateAppAbbr,
    handleCreateTicket,
    handleCancel,
  } = useApplyBase();

  const cloudInfo = reactive({
    id: '' as number | string,
    name: '',
  });
  const formdata = reactive(getInitFormdata());
  const formRef = ref();
  const rules = {
    'details.nodes.bookkeeper': [
      {
        validator: (value: Array<any>) => value.length >= 2,
        message: t('Bookkeeper节点数至少为2台'),
        trigger: 'change',
      },
    ],
    'details.nodes.zookeeper': [
      {
        validator: (value: Array<any>) => value.length === 3,
        message: t('Zookeeper节点数需3台'),
        trigger: 'change',
      },
    ],
    'details.nodes.broker': [
      {
        validator: (value: Array<any>) => value.length >= 1,
        message: t('Broker节点数至少为1台'),
        trigger: 'change',
      },
    ],
    'details.replication_num': [
      {
        validator: (value: number) => value <= formdata.details.nodes.bookkeeper.length,
        message: t('至少2_不能超过Bookkeeper数量'),
        trigger: 'change',
      },
    ],
    'details.ack_quorum': [
      {
        validator: (value: number) => value <= formdata.details.replication_num,
        message: t('写入成功副本数量小于等于副本数量'),
        trigger: 'change',
      },
    ],
  };

  /**
   * 切换业务，需要重置 IP 相关的选择
   */
  function handleChangeBiz(info: BizItem) {
    bizState.info = info;
    bizState.hasEnglishName = !!info.english_name;

    formdata.details.nodes.bookkeeper = [];
    formdata.details.nodes.broker = [];
    formdata.details.nodes.zookeeper = [];
  }
  /**
   * 变更所属管控区域
   */
  function handleChangeCloud(info: {id: number | string, name: string}) {
    cloudInfo.id = info.id;
    cloudInfo.name = info.name;

    formdata.details.nodes.bookkeeper = [];
    formdata.details.nodes.broker = [];
    formdata.details.nodes.zookeeper = [];
  }

  /**
   * pulsar 版本处理
   */
  const isDbVersionLoading = ref(true);
  const dbVersionList = shallowRef<Array<string>>([]);
  getVersions({
    query_key: 'pulsar',
  }).then((data) => {
    dbVersionList.value = data;
  })
    .finally(() => {
      isDbVersionLoading.value = false;
    });

  const makeMapByHostId = (hostList: Array<HostDetails>) =>  hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);
  // IP 选择器提交校验方法
  const ipSelectorDisabledSubmitMethods = {
    bookkeeper: (hostList: Array<any>) => (hostList.length >= 2 ? false : t('至少n台', { n: 2 })),
    broker: (hostList: Array<any>) => (hostList.length >= 1 ? false : t('至少n台', { n: 1 })),
    zookeeper: (hostList: Array<any>) => (hostList.length === 3 ? false : t('需n台', { n: 3 })),
  };
  // bookkeeper、zookeeper、broker 互斥
  const bookkeeperDisableHostMethod = (data: any) => {
    const zookeeperHostMap = makeMapByHostId(formdata.details.nodes.zookeeper);
    if (zookeeperHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Zookeeper']);
    }
    const brokerHostMap = makeMapByHostId(formdata.details.nodes.broker);
    if (brokerHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Broker']);
    }

    return false;
  };
  // bookkeeper、zookeeper、broker 互斥
  const zookeeperDisableHostMethod = (data: any, list: any[] = []) => {
    const bookkeeperHostMap = makeMapByHostId(formdata.details.nodes.bookkeeper);
    if (bookkeeperHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Bookkeeper']);
    }
    const brokerHostMap = makeMapByHostId(formdata.details.nodes.broker);
    if (brokerHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Broker']);
    }

    if (list.length >= 3 && !list.find(item => item.host_id === data.host_id)) {
      return t('需n台_已选n台', [3, list.length]);
    }

    return false;
  };
  // bookkeeper、zookeeper、broker 互斥
  const brokerDisableHostMethod = (data: any) => {
    const bookkeeperHostMap = makeMapByHostId(formdata.details.nodes.bookkeeper);
    if (bookkeeperHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Bookkeeper']);
    }
    const zookeeperHostMap = makeMapByHostId(formdata.details.nodes.zookeeper);
    if (zookeeperHostMap[data.host_id]) {
      return t('主机已被xx节点使用', ['Zookeeper']);
    }

    return false;
  };
  // 更新 bookkeeper 节点
  const handleBookkeeperIpListChange = (data: Array<HostDetails>) => {
    formdata.details.nodes.bookkeeper = data;
  };
  // 更新 zookeeper 节点
  const handleZookeeperIpListChange = (data: Array<HostDetails>) => {
    formdata.details.nodes.zookeeper = data;
  };
  // 更新 broker 节点
  const handleBrokerIpListChange = (data: Array<HostDetails>) => {
    formdata.details.nodes.broker = data;
  };

  const handleSubmit = () => {
    formRef.value.validate()
      .then(() => {
        baseState.isSubmitting = true;
        const mapIpField = (ipList: Array<HostDetails>) => ipList.map(item => ({
          bk_host_id: item.host_id,
          ip: item.ip,
          bk_cloud_id: item.cloud_area.id,
          bk_biz_id: item.biz.id,
        }));

        const params = {
          ...formdata,
          details: {
            ...formdata.details,
            nodes: {
              zookeeper: mapIpField(formdata.details.nodes.zookeeper),
              bookkeeper: mapIpField(formdata.details.nodes.bookkeeper),
              broker: mapIpField(formdata.details.nodes.broker),
            },
          },
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
.apply-pulsar {
  display: block;

  .db-card {
    & ~ .db-card {
      margin-top: 20px;
    }
  }

  :deep(.item-input) {
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
