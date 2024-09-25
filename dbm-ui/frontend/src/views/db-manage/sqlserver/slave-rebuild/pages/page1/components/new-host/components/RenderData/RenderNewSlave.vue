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
  <BkLoading :loading="isModuleLoading">
    <span
      v-bk-tooltips="{
        content: disabledTips,
        disabled: !disabledTips,
      }">
      <RenderElement
        ref="elementRef"
        :placeholder="t('请选择主机')"
        :rules="rules"
        @click="handleShowIpSelector">
        <span>{{ localHostData?.ip }}</span>
        <template #append>
          <DbIcon
            class="select-icon"
            type="host-select" />
        </template>
      </RenderElement>
    </span>
  </BkLoading>
  <IpSelector
    v-if="oldSlave"
    v-model:show-dialog="isShowIpSelector"
    :biz-id="currentBizId"
    button-text=""
    :cloud-info="{
      id: oldSlave.bkCloudId,
      name: oldSlave.bkCloudName,
    }"
    :disable-host-method="disableHostMethod"
    service-mode="all"
    :show-view="false"
    single-host-select
    @change="handleHostChange" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModuleDetail } from '@services/source/configs';
  import type { HostInfo } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import IpSelector from '@components/ip-selector/IpSelector.vue';
  import RenderElement from '@components/render-table/columns/element/Index.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    oldSlave?: IDataRow['oldSlave'];
  }

  interface Exposes {
    getValue: () => Promise<{
      new_slave_host: {
        bk_host_id: number;
        ip: string;
        bk_cloud_id: number;
      };
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const disabledTips = computed(() => (props.oldSlave ? '' : t('请先选择从库主机')));

  const disableHostMethod = (hostData: HostInfo) => {
    if (!hostModuleRelatedSystemVersion.value) {
      return t('获取从库主机操作系统失败');
    }
    const osName = hostData.os_name.replace(/ /g, '');
    if (
      !_.some(
        hostModuleRelatedSystemVersion.value.split(','),
        (moduleSystemVersion) => osName.indexOf(moduleSystemVersion) > -1,
      )
    ) {
      return t('操作系统仅支持 n', { n: hostModuleRelatedSystemVersion.value });
    }

    return false;
  };

  const elementRef = ref<ComponentExposed<typeof RenderElement>>();
  const isShowIpSelector = ref(false);

  const localHostData = shallowRef<HostInfo>();
  const hostModuleRelatedSystemVersion = ref('');

  const rules = [
    {
      validator: () => Boolean(localHostData.value?.ip),
      message: t('新从库主机不能为空'),
    },
  ];

  const { loading: isModuleLoading, run: fetchModuleDetail } = useRequest(getModuleDetail, {
    manual: true,
    onSuccess(result) {
      hostModuleRelatedSystemVersion.value = result.system_version;
    },
  });

  watch(
    () => props.oldSlave,
    (newData, oldData) => {
      if (newData && newData.dbModuleId !== oldData?.dbModuleId) {
        hostModuleRelatedSystemVersion.value = '';
        fetchModuleDetail({
          module_id: newData.dbModuleId,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleShowIpSelector = () => {
    if (disabledTips.value) {
      return;
    }
    isShowIpSelector.value = true;
  };

  const handleHostChange = (hostList: HostInfo[]) => {
    [localHostData.value] = hostList;
  };

  defineExpose<Exposes>({
    getValue() {
      return elementRef.value!.getValue().then(() => ({
        new_slave_host: {
          bk_biz_id: localHostData.value!.biz.id,
          bk_cloud_id: localHostData.value!.cloud_id,
          bk_host_id: localHostData.value!.host_id,
          ip: localHostData.value!.ip,
        },
      }));
    },
  });
</script>
