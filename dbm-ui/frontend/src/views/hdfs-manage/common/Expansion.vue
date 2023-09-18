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
  <div class="hdfs-cluster-expansion-box">
    <DbForm
      form-type="vertical"
      :model="formData">
      <DbFormItem label="Datanodes">
        <IpSelector
          :biz-id="bizId"
          :cloud-info="{
            id: data.bk_cloud_id,
            name: data.bk_cloud_name
          }"
          :data="formData.details.nodes.datanode"
          required
          :show-view="false"
          @change="handleDatanodeChange" />
        <RenderHostTable v-model:data="formData.details.nodes.datanode" />
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

  import { createTicket } from '@services/ticket';
  import type { HdfsDetail } from '@services/types/hdfs';
  import type { HostDetails } from '@services/types/ip';

  import { useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import RenderHostTable from '@components/cluster-common/big-data-host-table/RenderHostTable.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import { messageError } from '@utils';

  interface Props {
    data: HdfsDetail,
  }
  interface Emits {
    (e: 'change'): void
  }
  interface Exposes {
    submit: () => Promise<any>
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const globalBizsStore = useGlobalBizs();
  const bizId = globalBizsStore.currentBizId;
  const ticketMessage = useTicketMessage();
  const { t } = useI18n();

  const isLoading = ref(false);

  const formData = reactive({
    details: {
      ip_source: 'manual_input',
      cluster_id: props.data.id,
      nodes: {
        datanode: [] as Array<HostDetails>,
      },
    },
    remark: '',
  });

  const handleDatanodeChange = (hostList: Array<HostDetails>) => {
    formData.details.nodes.datanode = hostList;
  };

  defineExpose<Exposes>({
    submit() {
      return new Promise((resolve, reject) => {
        if (formData.details.nodes.datanode.length < 1) {
          messageError(t('DataNodes节点IP不能为空'));
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
            createTicket({
              ticket_type: 'HDFS_SCALE_UP',
              bk_biz_id: bizId,
              ...formData,
              details: {
                ...formData.details,
                nodes: {
                  datanode: formData.details.nodes.datanode.map(item => ({
                    bk_host_id: item.host_id,
                    ip: item.ip,
                    bk_cloud_id: item.cloud_area.id,
                  })),
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
  .hdfs-cluster-expansion-box {
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
