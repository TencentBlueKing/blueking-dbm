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
  <div>
    <IpSelector
      :biz-id="bizId"
      class="mt-12"
      :cloud-info="cloudInfo"
      :disable-host-method="disableHostMethod"
      :show-view="false"
      @change="handleHostChange">
      <template #submitTips="{ hostList }">
        <I18nT
          keypath="已选n台_共nGB(目标容量:nG)"
          style="font-size: 14px; color: #63656e"
          tag="span">
          <span
            class="number"
            style="color: #2dcb56">
            {{ hostList.length }}
          </span>
          <span
            class="number"
            style="color: #3a84ff">
            {{ calcSelectHostDisk(hostList) }}
          </span>
          <span
            class="number"
            style="color: #63656e">
            {{ data.targetDisk - data.totalDisk }}
          </span>
        </I18nT>
      </template>
    </IpSelector>
    <div
      v-if="hostTableData.length > 0"
      class="data-preview-table">
      <div class="data-preview-header">
        <I18nT keypath="共n台_共nGB">
          <span
            class="number"
            style="color: #3a84ff">
            {{ hostTableData.length }}
          </span>
          <span
            class="number"
            style="color: #2dcb56">
            {{ calcSelectHostDisk(hostTableData) }}
          </span>
        </I18nT>
        <I18nT
          v-if="targetMatchReal > 0"
          class="ml-8"
          keypath="较目标容量相差nG">
          <span
            class="number"
            style="color: #ff9c01">
            {{ targetMatchReal }}
          </span>
        </I18nT>
        <I18nT
          v-if="targetMatchReal < 0"
          class="ml-8"
          keypath="较目标容量超出nG">
          <span
            class="number"
            style="color: #ff9c01">
            {{ Math.abs(targetMatchReal) }}
          </span>
        </I18nT>
      </div>
      <BkTable
        :columns="tableColumns"
        :data="hostTableData" />
    </div>
  </div>
</template>
<script setup lang="tsx">
  import {
    computed,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { HostDetails } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import type { TExpansionNode } from '@components/cluster-common/host-expansion/Index.vue'
  import HostAgentStatus from '@components/cluster-common/HostAgentStatus.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  interface Props {
    cloudInfo: {
      id: number,
      name: string
    },
    data: TExpansionNode,
    disableHostMethod?: (params: TExpansionNode['hostList'][0]) => string | boolean
  }

  interface Emits {
    (e: 'change', value: TExpansionNode['hostList'], expansionDisk: TExpansionNode['expansionDisk']): void,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const calcSelectHostDisk = (hostList: TExpansionNode['hostList']) => hostList
    .reduce((result, hostItem) => result + Math.floor(Number(hostItem.bk_disk || 0)), 0)

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const bizId = globalBizsStore.currentBizId;

  const hostTableData = shallowRef<TExpansionNode['hostList']>(props.data.hostList || []);

  // 目标容量和实际容量误差
  const targetMatchReal = computed(() => {
    const {
      totalDisk,
      targetDisk,
      expansionDisk,
    } = props.data;

    const realTargetDisk = totalDisk + expansionDisk;
    return targetDisk - realTargetDisk;
  });

  const tableColumns = [
    {
      label: t('节点 IP'),
      field: 'ip',
      render: ({ data }: {data: HostDetails}) => data.ip || '--',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: { data: HostDetails }) => <HostAgentStatus data={data.alive} />,
    },
    {
      label: t('磁盘_GB'),
      field: 'bk_disk',
      render: ({ data }: {data: HostDetails}) => data.bk_disk || '--',
    },
    {
      label: t('操作'),
      width: 100,
      render: ({ data }: {data: HostDetails}) => (
        <bk-button
          text
          theme="primary"
          onClick={() => handleRemoveHost(data)}>
          {t('删除')}
        </bk-button>
      ),
    },
  ];

  const handleHostChange = (hostList: TExpansionNode['hostList']) => {
    hostTableData.value = hostList;
    emits('change', hostList, calcSelectHostDisk(hostList));
  };

  const handleRemoveHost = (data: TExpansionNode['hostList'][0]) => {
    const hostList = hostTableData.value.reduce((result, item) => {
      if (item.host_id !== data.host_id) {
        result.push(item);
      }
      return result;
    }, [] as TExpansionNode['hostList']);
    hostTableData.value = hostList;
    emits('change', hostList, calcSelectHostDisk(hostList));
  };
</script>
