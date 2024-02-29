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
  <div class="add-nodes">
    <NodeNumber :id="data.id" />
    <DbForm
      ref="formRef"
      form-type="vertical"
      :model="formData"
      :rules="formRules">
      <BkFormItem
        :label="t('服务器选择')"
        property="ip_source"
        required>
        <BkRadioGroup v-model="formData.ip_source">
          <BkRadioButton label="resource_pool">
            {{ t('自动从资源池匹配') }}
          </BkRadioButton>
          <BkRadioButton label="manual_input">
            {{ t('业务空闲机') }}
          </BkRadioButton>
        </BkRadioGroup>
      </BkFormItem>
      <Transition
        mode="out-in"
        name="dbm-fade">
        <div
          v-if="formData.ip_source === 'resource_pool'"
          class="mb-24">
          <BkFormItem
            :label="t('资源规格')"
            property="spec_id"
            required>
            <SpecSelector
              ref="specRef"
              v-model="formData.spec_id"
              :biz-id="currentBizId"
              :cloud-id="data.bk_cloud_id"
              :cluster-type="ClusterTypes.RIAK"
              machine-type="riak"
              style="width: 100%" />
          </BkFormItem>
          <BkFormItem
            :label="t('节点数量')"
            property="count"
            required>
            <BkInput
              v-model="formData.count"
              class="mb10"
              clearable
              :max="100"
              :min="1"
              type="number" />
          </BkFormItem>
        </div>
        <div
          v-else
          class="mb-24">
          <BkFormItem
            ref="nodesRef"
            :label="t('服务器')"
            property="nodes"
            required>
            <IpSelector
              :biz-id="currentBizId"
              :cloud-info="{
                id: data.bk_cloud_id,
                name: data.bk_cloud_name,
              }"
              :data="formData.nodes"
              :disable-dialog-submit-method="disableHostSubmitMethods"
              @change="handleProxyIpChange">
              <template #desc>
                {{ t('至少n台', { n: 1 }) }}
              </template>
              <template #submitTips="{ hostList }">
                <I18nT
                  keypath="至少n台_已选n台"
                  style="font-size: 14px; color: #63656e"
                  tag="span">
                  <span style="font-weight: bold; color: #2dcb56"> 1 </span>
                  <span style="font-weight: bold; color: #3a84ff"> {{ hostList.length }} </span>
                </I18nT>
              </template>
            </IpSelector>
          </BkFormItem>
        </div>
      </Transition>
    </DbForm>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RiakModel from '@services/model/riak/riak';
  import { createTicket } from '@services/source/ticket';
  import type { HostDetails } from '@services/types';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import SpecSelector from '@components/apply-items/SpecSelector.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import NodeNumber from './components/NodeNumber.vue';

  interface Props {
    data: RiakModel;
  }

  interface Emits {
    (e: 'submitSuccess'): void;
  }

  interface Expose {
    submit: () => Promise<boolean | void | undefined>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const formRules = {
    nodes_num: [
      {
        validator: (value: number) => value >= 1,
        message: t('节点数至少为n台', [1]),
        trigger: 'change',
      },
    ],
    nodes: [
      {
        validator: (value: HostDetails[]) => value.length >= 1,
        message: t('节点数至少为n台', [1]),
        trigger: 'change',
      },
    ],
  };

  const formRef = ref();
  const nodesRef = ref();
  const formData = reactive({
    ip_source: 'resource_pool',
    spec_id: '',
    count: 1,
    nodes: [] as HostDetails[],
  });

  const disableHostSubmitMethods = (hostList: Array<HostDetails[]>) =>
    hostList.length < 1 ? t('至少n台', { n: 1 }) : false;

  const handleProxyIpChange = (data: HostDetails[]) => {
    formData.nodes = data;
    if (formData.nodes.length > 0) {
      nodesRef.value.clearValidate();
    }
  };

  defineExpose<Expose>({
    async submit() {
      await formRef.value.validate();

      const { ip_source: ipSource } = formData;
      const params = {
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.RIAK_CLUSTER_SCALE_OUT,
        details: {
          ip_source: ipSource,
          cluster_id: props.data.id,
        },
      };

      if (ipSource === 'resource_pool') {
        Object.assign(params.details, {
          resource_spec: {
            riak: {
              count: formData.count,
              spec_id: formData.spec_id,
            },
          },
        });
      } else {
        Object.assign(params.details, {
          nodes: {
            riak: formData.nodes.map((nodeItem) => ({
              ip: nodeItem.ip,
              bk_host_id: nodeItem.host_id,
              bk_cloud_id: nodeItem.cloud_id,
              alive: nodeItem.alive,
              bk_disk: nodeItem.bk_disk,
            })),
          },
        });
      }

      return createTicket(params).then((createTicketResult) => {
        ticketMessage(createTicketResult.id);
        emits('submitSuccess');
      });
    },
  });
</script>

<style lang="less" scoped>
  .add-nodes {
    padding: 0 40px;
  }
</style>
