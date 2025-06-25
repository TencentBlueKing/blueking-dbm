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
            {{ t('资源池自动匹配') }}
          </BkRadioButton>
          <BkRadioButton label="manual_input">
            {{ t('资源池手动选择') }}
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
            <BkButton @click="handleShowSelector">
              <i class="db-icon-add" />
              {{ t('添加服务器') }}
            </BkButton>
            <ResourceHostSelector
              v-model:is-show="isShowSelector"
              :params="{
                for_bizs: [currentBizId, 0],
                resource_types: [DBTypes.RIAK, 'PUBLIC'],
              }"
              :selected="formData.nodes"
              @change="handleHostChange" />
            <BkTable
              v-if="formData.nodes.length"
              class="mt-16"
              :data="formData.nodes">
              <BkTableColumn
                field="ip"
                :label="t('节点 IP')"
                :min-width="150"
                :width="250" />
              <BkTableColumn
                field="agent_status"
                :label="t('Agent状态')"
                :min-width="150">
                <template #default="{ row }">
                  <RenderHostStatus :data="row.agent_status" />
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="bk_disk"
                :label="t('磁盘容量(G)')"
                :min-width="150" />
              <BkTableColumn
                :label="t('操作')"
                :min-width="150">
                <template #default="{ row }">
                  <BkButton
                    text
                    theme="primary"
                    @click="handleDeleteNode(row)">
                    {{ t('删除') }}
                  </BkButton>
                </template>
              </BkTableColumn>
            </BkTable>
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
  import type { HostInfo } from '@services/types';

  import { useTicketMessage } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import RenderHostStatus from '@components/render-host-status/Index.vue';
  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  import SpecSelector from '@views/db-manage/common/apply-items/SpecSelector.vue';

  import NodeNumber from './NodeNumber.vue';

  interface Props {
    data: RiakModel;
  }

  type Emits = (e: 'submitSuccess') => void;

  interface Expose {
    submit: () => Promise<boolean | void | undefined>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;
  const ticketMessage = useTicketMessage();

  const formRules = {
    nodes: [
      {
        message: t('节点数至少为n台', [1]),
        trigger: 'change',
        validator: (value: HostInfo[]) => value.length >= 1,
      },
    ],
    nodes_num: [
      {
        message: t('节点数至少为n台', [1]),
        trigger: 'change',
        validator: (value: number) => value >= 1,
      },
    ],
  };

  const formRef = ref();
  const nodesRef = ref();
  const formData = reactive({
    count: 1,
    ip_source: 'resource_pool',
    nodes: [] as IValue[],
    spec_id: '',
  });
  const isShowSelector = ref(false);

  const handleShowSelector = () => {
    isShowSelector.value = true;
  };

  const handleHostChange = (data: IValue[]) => {
    formData.nodes = data;
    if (formData.nodes.length > 0) {
      nodesRef.value.clearValidate();
    }
  };

  const handleDeleteNode = (row: IValue) => {
    formData.nodes = formData.nodes.filter((nodeItem) => nodeItem.ip !== row.ip);
  };

  defineExpose<Expose>({
    async submit() {
      await formRef.value.validate();

      const { ip_source: ipSource } = formData;
      const params = {
        bk_biz_id: currentBizId,
        details: {
          cluster_id: props.data.id,
          ip_source: 'resource_pool',
        },
        ticket_type: TicketTypes.RIAK_CLUSTER_SCALE_OUT,
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
          resource_spec: {
            riak: {
              count: formData.nodes.length,
              hosts: formData.nodes.map((nodeItem) => ({
                agent_status: nodeItem.agent_status,
                bk_cloud_id: nodeItem.bk_cloud_id,
                bk_disk: nodeItem.bk_disk,
                bk_host_id: nodeItem.bk_host_id,
                ip: nodeItem.ip,
              })),
              spec_id: 1,
            },
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
