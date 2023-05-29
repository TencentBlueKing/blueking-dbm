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
  <div class="es-cluster-expansion-box">
    <BkAlert
      class="mb16"
      theme="warning"
      :title="$t('冷热节点_至少添加一种节点IP')" />
    <DbForm
      form-type="vertical"
      :model="formData">
      <DbFormItem :label="$t('热节点')">
        <IpSelector
          :biz-id="bizId"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name
          }"
          :disable-host-method="hotDisableHostMethod"
          required
          :show-view="false"
          @change="handleHotChange" />
        <WithInstanceHostTable
          v-model:data="formData.details.nodes.hot"
          :biz-id="bizId" />
      </DbFormItem>
      <DbFormItem :label="$t('冷节点')">
        <IpSelector
          :biz-id="bizId"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name
          }"
          :disable-host-method="coldDisableHostMethod"
          :show-view="false"
          @change="handleColdChange" />
        <WithInstanceHostTable
          v-model:data="formData.details.nodes.cold"
          :biz-id="bizId" />
      </DbFormItem>
      <DbFormItem :label="$t('备注')">
        <BkInput
          v-model="formData.remark"
          :maxlength="100"
          :placeholder="$t('请提供更多有用信息申请信息_以获得更快审批')"
          type="textarea" />
      </DbFormItem>
    </DbForm>
  </div>
</template>
<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import {
    reactive,
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type EsModel from '@services/model/es/es';
  import { createTicket } from '@services/ticket';
  import type { HostDetails } from '@services/types/ip';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import WithInstanceHostTable, {
    type IHostTableDataWithInstance,
  } from '@components/cluster-common/big-data-host-table/es-host-table/index.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import { messageError } from '@utils';


  interface Props {
    data: EsModel,
  }
  interface Emits {
    (e: 'change'): void
  }
  interface Exposes {
    submit: () => Promise<any>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const formatIpDataWidthInstance = (data: Array<HostDetails>) => data.map(item => ({
    instance_num: 1,
    ...item,
  }));

  const makeMapByHostId = (hostList: Array<HostDetails>) =>  hostList.reduce((result, item) => ({
    ...result,
    [item.host_id]: true,
  }), {} as Record<number, boolean>);

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const ticketMessage = useTicketMessage();

  const bizId = globalBizsStore.currentBizId;

  const isLoading = ref(false);

  const formData = reactive({
    details: {
      ip_source: 'manual_input',
      cluster_id: props.data.id,
      nodes: {
        hot: [] as Array<IHostTableDataWithInstance>,
        cold: [] as Array<IHostTableDataWithInstance>,
      },
    },
    remark: '',
  });

  // 热节点、冷节点互斥
  const hotDisableHostMethod = (data: any) => {
    const coldHostMap = makeMapByHostId(formData.details.nodes.cold);
    if (coldHostMap[data.host_id]) {
      return t('主机已被冷节点使用');
    }

    return false;
  };

  // 热节点、冷节点互斥
  const coldDisableHostMethod = (data: any) => {
    const hotHostMap = makeMapByHostId(formData.details.nodes.hot);
    if (hotHostMap[data.host_id]) {
      return t('主机已被热节点使用');
    }
    return false;
  };

  const handleHotChange = (hostList: Array<HostDetails>) => {
    formData.details.nodes.hot = formatIpDataWidthInstance(hostList);
  };

  const handleColdChange = (hostList: Array<HostDetails>) => {
    formData.details.nodes.cold = formatIpDataWidthInstance(hostList);
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        if (formData.details.nodes.hot.length < 1 && formData.details.nodes.cold.length < 1) {
          messageError(t('冷热节点_至少添加一种节点IP'));
          return reject();
        }
        isLoading.value = true;
        InfoBox({
          title: t('确认扩容集群'),
          subTitle: '',
          confirmText: t('确认'),
          cancelText: t('取消'),
          headerAlign: 'center',
          contentAlign: 'center',
          footerAlign: 'center',
          onClosed: () => reject(),
          onConfirm: () => {
            const mapIpFieldWithInstance = (ipList: Array<IHostTableDataWithInstance>) => ipList.map(item => ({
              bk_host_id: item.host_id,
              ip: item.ip,
              bk_cloud_id: item.cloud_area.id,
              instance_num: item.instance_num,
            }));
            createTicket({
              ticket_type: 'ES_SCALE_UP',
              bk_biz_id: bizId,
              ...formData,
              details: {
                ...formData.details,
                nodes: {
                  hot: mapIpFieldWithInstance(formData.details.nodes.hot),
                  cold: mapIpFieldWithInstance(formData.details.nodes.cold),
                },
              },
            }).then((data) => {
              ticketMessage(data.id);
              resolve('success');
              emits('change');
            })
              .catch(() => {
                reject();
              });
          },
        });
      });
    },
  });
</script>
<style lang="less">
  .es-cluster-expansion-box {
    padding: 18px 43px 18px 37px;
    font-size: 12px;
    line-height: 20px;
    color: #63656e;

    .item {
      & ~ .item {
        margin-top: 24px;
      }

      .item-label {
        margin-bottom: 6px;
      }
    }
  }
</style>
