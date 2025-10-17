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
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableBlock
      v-model="localValue"
      :placeholder="t('选择后生成')">
      <template #append>
        <DbIcon
          class="select-icon"
          type="host-select"
          @click="handleShowSelector" />
      </template>
    </EditableBlock>
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

  type Emits = (e: 'batch-edit', list: HostInfo[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const isShowIpSelector = ref(false);
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

  const handleHostChange = (hostList: HostInfo[]) => {
    selected.value = hostList;
    modelValue.value = hostList.map((item) => item.ip);
    emits('batch-edit', hostList);
  };

  const handleWhitelistChange = (whiteList: IPSelectorResult['dbm_whitelist']) => {
    const finalIps = _.union(
      selected.value.map((item) => item.ip),
      _.flatMap(whiteList, 'ips'),
    );
    selected.value = finalIps.map((ip) => ({ ip }) as HostInfo);
    modelValue.value = finalIps;
    emits('batch-edit', selected.value);
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

  .select-icon {
    display: flex;
    margin-right: 5px;
    font-size: 18px;
    color: #979ba5;
    align-items: center;
    cursor: pointer;

    &:hover {
      color: #3a84ff;
    }
  }
</style>
