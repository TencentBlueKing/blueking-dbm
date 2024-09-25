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
  <div class="render-host-box">
    <TableSeletorInput
      ref="editRef"
      v-model="localValue"
      :placeholder="placeholder"
      :rules="rules"
      :tooltip-content="t('选择主机')"
      @click-seletor="handleShowIpSelector" />
  </div>
  <IpSelector
    v-if="clusterData"
    v-model:show-dialog="isShowIpSelector"
    :biz-id="currentBizId"
    button-text=""
    :cloud-info="{
      id: clusterData.cloudId,
      name: clusterData.cloudName,
    }"
    :data="localHostList"
    :os-types="[OSTypes.Linux]"
    service-mode="idle_only"
    :show-view="false"
    :single-host-select="single"
    @change="handleHostChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkHost } from '@services/source/ipchooser';
  import type { HostInfo } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import { OSTypes } from '@common/const';
  import { batchSplitRegex, ipv4 } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import TableSeletorInput from '@views/db-manage/common/TableSeletorInput.vue';

  import type { IDataRow } from '../render-data/Index.vue';

  export interface HostDataItem {
    bk_host_id: number;
    ip: string;
    bk_cloud_id: number;
    bk_biz_id: number;
  }

  interface Props {
    clusterData: IDataRow['clusterData'];
    single?: boolean;
    hostData: HostDataItem[];
  }

  interface Exposes {
    getValue: () => Promise<{
      hosts: HostDataItem[];
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    single: false,
    hostData: undefined,
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('IP 不能为空'),
    },
    {
      validator: (value: string) => value.split(',').every((ip) => ipv4.test(ip)),
      message: t('IP 格式不符合IPv4标准'),
    },
    {
      validator: async (value: string) => {
        const list = value.split(batchSplitRegex);
        return await checkHost({
          ip_list: list,
        }).then((data) => {
          if (data.length === list.length) {
            allocatData(data);
            return true;
          }
          return false;
        });
      },
      message: t('主机不存在'),
    },
  ];

  const editRef = ref();
  const isShowIpSelector = ref(false);
  const localValue = ref();
  const localHostList = shallowRef<HostInfo[]>([]);

  const placeholder = computed(() => (props.single ? t('请输入或选择 (1台)') : t('请输入或选择')));

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  // 批量选择
  const handleHostChange = (hostList: HostInfo[]) => {
    allocatData(hostList);
    window.changeConfirm = true;
    setTimeout(() => {
      editRef.value.getValue();
    });
  };

  const allocatData = (data: HostInfo[]) => {
    localValue.value = data.map((item) => item?.ip).join(',');
    localHostList.value = data;
  };

  watch(
    () => props.hostData,
    (data) => {
      const fristHost = data?.[0];
      if (!fristHost?.ip) {
        return;
      }
      allocatData(data as unknown as HostInfo[]);
    },
    {
      immediate: true,
    },
  );

  defineExpose<Exposes>({
    getValue() {
      const formatHost = (hostList: HostInfo[]) =>
        hostList.map((item) => ({
          bk_host_id: item.host_id,
          ip: item.ip,
          bk_cloud_id: item.cloud_area.id,
          bk_biz_id: currentBizId,
        }));

      return Promise.resolve({
        hosts: formatHost(localHostList.value),
      });
    },
  });
</script>
<style lang="less" scoped>
  .render-host-box {
    position: relative;

    :deep(.is-error) {
      .input-error {
        right: 10px;
      }
    }
  }
</style>
