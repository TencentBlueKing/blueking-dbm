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
  <div class="influxdb-replace">
    <template v-if="!isEmpty">
      <DbForm
        form-type="vertical"
        :model="formdata">
        <BkFormItem label="">
          <RenderNodeHostList
            ref="influxdbRef"
            v-model:hostList="formdata.influxdb.hostList"
            v-model:nodeList="formdata.influxdb.nodeList"
            @remove-node="handleRemoveNode" />
        </BkFormItem>
        <BkFormItem :label="$t('备注')">
          <BkInput
            v-model="formdata.remark"
            :maxlength="100"
            :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
            type="textarea" />
        </BkFormItem>
      </DbForm>
    </template>
    <div
      v-else
      class="node-empty">
      <BkException
        scene="part"
        type="empty">
        <template #description>
          <DbIcon
            class="mr-4"
            type="attention" />
          <span>{{ t('请先返回列表选择要替换的节点') }}</span>
        </template>
      </BkException>
    </div>
  </div>
</template>
<script setup lang="ts">
  import {
    computed,
    reactive,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type InfluxDBInstanceModel from '@services/model/influxdb/influxdbInstance';
  import { createTicket } from '@services/ticket';
  import type { HostDetails } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import { messageError  } from '@utils';

  import RenderNodeHostList from './components/RenderNodeHostList.vue';

  import { useInfo, useTicketMessage } from '@/hooks';

  export interface TNodeInfo {
    nodeList: InfluxDBInstanceModel[],
    hostList: HostDetails[],
  }

  interface Props {
    nodeList: Array<InfluxDBInstanceModel>
  }

  interface Emits {
    (e: 'removeNode', bkHostId: number): void,
    (e: 'succeeded'): void
  }

  interface Exposes {
    submit: () => Promise<any>,
    cancel: () => Promise<any>,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const influxdbRef = ref();
  const formdata = reactive({
    remark: '',
    influxdb: {
      nodeList: [],
      hostList: [],
    } as TNodeInfo,
  });
  const isEmpty = computed(() => formdata.influxdb.nodeList.length < 1);

  watch(isEmpty, () => {
    if (isEmpty.value) {
      nextTick(() => {
        window.changeConfirm = false;
      });
    }
  });

  watch(() => props.nodeList, () => {
    formdata.influxdb.nodeList = props.nodeList;
  }, {
    immediate: true,
  });

  const handleRemoveNode = (instanceId: number) => {
    emits('removeNode', instanceId);
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        const influxdb = influxdbRef.value ? influxdbRef.value.getValue() : {};

        if (influxdb.new_nodes?.length < 1) {
          messageError(t('替换节点不能为空'));
          return reject();
        }

        useInfo({
          width: 480,
          title: t('确认替换n个实例IP', { n: influxdb.old_nodes.length }),
          content: t('替换后_原实例IP将不再可用_资源将会被释放'),
          onConfirm: () => createTicket({
            ticket_type: 'INFLUXDB_REPLACE',
            bk_biz_id: currentBizId,
            details: {
              ip_source: 'manual_input',
              old_nodes: {
                influxdb: influxdb.old_nodes,
              },
              new_nodes: {
                influxdb: influxdb.new_nodes,
              },
            },
            remark: formdata.remark,
          })
            .then((res) => {
              ticketMessage(res.id);
              resolve('success');
              emits('succeeded');
              return true;
            })
            .catch(() => {
              reject();
              return false;
            }),
          onCancel: () => {
            reject();
          },
        });
      });
    },
    cancel() {
      return Promise.resolve();
    },
  });
</script>

<style lang="less" scoped>
  .influxdb-replace {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;

    .node-empty {
      height: calc(100vh - 58px);
      padding-top: 168px;
    }
  }
</style>
