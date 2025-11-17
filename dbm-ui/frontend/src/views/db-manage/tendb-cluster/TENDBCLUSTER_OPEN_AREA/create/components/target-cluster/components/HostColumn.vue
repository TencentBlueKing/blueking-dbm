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
  <EditableColumn
    :disabled-method="disabledMethod"
    field="authorize_ips"
    :label="t('授权 IP')"
    :min-width="200">
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowBatchSelector">
        <DbIcon type="bulk-edit" />
      </span>
      <!-- 批量选择 -->
      <IpSelector
        v-model:show-dialog="isShowBatchIpSelector"
        :biz-id="cluster.bk_biz_id"
        button-text=""
        :cloud-info="{
          id: cluster.bk_cloud_id,
          name: cluster.bk_cloud_name,
        }"
        :data="batchSelected"
        :only-alive-host="false"
        :panel-list="['staticTopo', 'dbmWhitelist', 'manualInput']"
        service-mode="all"
        :show-view="false"
        @change="handleHostBatchChange"
        @change-whitelist="handleWhitelistBatchChange" />
    </template>
    <EditableBlock
      v-model="localValue"
      class="host-block"
      :placeholder="t('请选择 IP')"
      @click="handleShowSelector">
      <template #append>
        <DbIcon
          class="angle-down"
          size="small"
          type="bk-dbm-icon db-icon-down-big" />
      </template>
    </EditableBlock>
    <!-- 单行选择 -->
    <IpSelector
      v-model:show-dialog="isShowIpSelector"
      :biz-id="cluster.bk_biz_id"
      button-text=""
      :cloud-info="{
        id: cluster.bk_cloud_id,
        name: cluster.bk_cloud_name,
      }"
      :data="selected"
      :only-alive-host="false"
      :panel-list="['staticTopo', 'dbmWhitelist', 'manualInput']"
      service-mode="all"
      :show-view="false"
      @change="handleHostChange"
      @change-whitelist="handleWhitelistChange" />
  </EditableColumn>
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import { checkHost } from '@services/source/ipchooser';
  import type { HostInfo } from '@services/types';

  import IpSelector, { type IPSelectorResult } from '@components/ip-selector/IpSelector.vue';

  interface Props {
    cluster: TendbclusterModel;
    selectedIps: string[];
  }

  type Emits = (e: 'batch-edit', ips: string[], field: 'authorize_ips') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const isShowBatchIpSelector = ref(false);
  const isShowIpSelector = ref(false);
  const batchSelected = shallowRef<HostInfo[]>([]);
  const selected = shallowRef<HostInfo[]>([]);
  const localValue = computed(() => modelValue.value.join(','));

  const { run: queryHost } = useRequest(checkHost, {
    manual: true,
    onSuccess: (data) => {
      selected.value = data;
    },
  });

  const disabledMethod = (rowData?: any) => {
    if (!rowData.cluster.id) {
      return t('请先选择集群');
    }
    return '';
  };

  const handleShowSelector = () => {
    isShowIpSelector.value = true;
  };

  const handleShowBatchSelector = () => {
    isShowBatchIpSelector.value = true;
  };

  const handleHostChange = (hostList: HostInfo[]) => {
    selected.value = hostList;
    modelValue.value = hostList.map((item) => item.ip);
  };

  const handleHostBatchChange = (hostList: HostInfo[]) => {
    batchSelected.value = hostList;
    emits(
      'batch-edit',
      hostList.map((item) => item.ip),
      'authorize_ips',
    );
  };

  const handleWhitelistChange = (whiteList: IPSelectorResult['dbm_whitelist']) => {
    const finalIps = _.union(
      selected.value.map((item) => item.ip),
      _.flatMap(whiteList, 'ips'),
    );
    selected.value = finalIps.map((ip) => ({ ip }) as HostInfo);
    modelValue.value = finalIps;
  };

  const handleWhitelistBatchChange = (whiteList: IPSelectorResult['dbm_whitelist']) => {
    const finalIps = _.union(
      batchSelected.value.map((item) => item.ip),
      _.flatMap(whiteList, 'ips'),
    );
    batchSelected.value = finalIps.map((ip) => ({ ip }) as HostInfo);
    emits('batch-edit', finalIps, 'authorize_ips');
  };

  watch(
    () => props.selectedIps,
    async () => {
      if (props.selectedIps.length) {
        queryHost({
          ip_list: props.selectedIps,
          mode: 'all',
          scope_list: [
            {
              scope_id: window.PROJECT_CONFIG.BIZ_ID,
              scope_type: 'biz',
            },
          ],
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .batch-host-select {
    font-size: 14px;
    color: #3a84ff;
    cursor: pointer;
  }

  .host-block {
    cursor: pointer;
  }
</style>
