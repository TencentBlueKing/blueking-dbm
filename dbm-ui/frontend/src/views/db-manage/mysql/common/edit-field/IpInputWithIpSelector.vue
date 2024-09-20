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
  <TableEditInput
    ref="inputRef"
    v-model="localValue"
    class="cluster-name-with-selector"
    :placeholder="t('请输入或选择主机')"
    :rules="rules"
    @blur="() => (isFocused = false)"
    @error="handleInputError"
    @focus="() => (isFocused = true)">
    <template #suspend>
      <BkPopover
        v-if="!isFocused"
        :content="t('从业务拓扑选择')"
        placement="top"
        :popover-delay="0">
        <div class="edit-btn-wraper">
          <div
            class="edit-btn"
            @click="handleClickSeletor">
            <div class="edit-btn-inner">
              <DbIcon
                class="select-icon"
                type="host-select" />
            </div>
          </div>
        </div>
      </BkPopover>
    </template>
  </TableEditInput>
  <IpSelector
    v-model:show-dialog="isShowSelecotr"
    :biz-id="currentBizId"
    button-text=""
    :cloud-info="{
      id: cloudInfo?.cloudId,
      name: cloudInfo?.cloudName,
    }"
    :os-types="[OSTypes.Linux]"
    service-mode="all"
    :show-view="false"
    :single-host-select="!multiple"
    @change="handleHostChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { checkMysqlInstances } from '@services/source/instances';
  import type { HostDetails } from '@services/types';

  import { OSTypes } from '@common/const';
  import { ipv4 } from '@common/regex';

  import IpSelector from '@components/ip-selector/IpSelector.vue';
  import TableEditInput from '@components/render-table/columns/input/index.vue';

  export interface IpBasicInfo {
    bk_biz_id?: number;
    bk_cloud_id: number;
    bk_host_id?: number;
    ip: string;
  }

  interface Props {
    cloudInfo?: {
      cloudId: number;
      cloudName: string;
    };
    multiple?: boolean;
    type?: 'ip' | 'cloud-ip'; // ip: ip; cloud-ip: cloud:ip
  }

  interface Emits {
    (e: 'ipChange', value: IpBasicInfo): void;
    (e: 'error', value: boolean): void;
  }

  interface Exposes {
    getValue: () => Promise<IpBasicInfo>;
    focus: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    multiple: false,
    type: 'ip',
    cloudInfo: undefined,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IpBasicInfo>({
    default: {
      bk_cloud_id: 0,
      ip: '',
    },
  });

  const { t } = useI18n();

  const inputRef = ref();
  const isFocused = ref(false);
  const isShowSelecotr = ref(false);
  const localValue = ref('');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const rules = [
    {
      validator: (value: string) => !!value,
      message: t('不能为空'),
    },
    {
      validator: (ip: string) => {
        if (props.type === 'ip') {
          return true;
        }

        const items = ip.split(':');
        return items.length === 2 && /^\d+$/.test(items[0]);
      },
      message: t('请输入xx', [t('管控区域')]),
      trigger: 'blur',
    },
    {
      validator: (value: string) => {
        let ip = value;
        if (props.type === 'cloud-ip') {
          ip = value.split(':')[1];
        }
        return ipv4.test(ip);
      },
      message: t('IP格式不正确'),
    },
    {
      validator: (value: string) => {
        let ip = value;
        if (props.type === 'cloud-ip') {
          ip = value.split(':')[1];
        }
        return checkMysqlInstances({
          bizId: window.PROJECT_CONFIG.BIZ_ID,
          instance_addresses: [ip],
        }).then((data) => {
          if (data.length < 1) {
            return false;
          }
          const [instanceData] = data;
          if (!modelValue.value?.ip || modelValue.value.ip !== instanceData.ip) {
            modelValue.value = {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: instanceData.bk_cloud_id,
              bk_host_id: instanceData.bk_host_id,
              ip: instanceData.ip,
            };
            emits('ipChange', modelValue.value);
          }
          return true;
        });
      },
      message: t('IP不存在'),
    },
  ];

  watch(
    () => modelValue.value,
    () => {
      if (!modelValue.value) {
        return;
      }

      if (props.type === 'cloud-ip' && modelValue.value.ip) {
        localValue.value = `${modelValue.value.bk_cloud_id}:${modelValue.value.ip}`;
      } else {
        localValue.value = modelValue.value.ip;
      }
    },
    {
      immediate: true,
    },
  );

  const handleClickSeletor = () => {
    isShowSelecotr.value = true;
  };

  const handleHostChange = (hostList: HostDetails[]) => {
    const host = hostList[0];
    localValue.value = host.ip;
    modelValue.value = {
      bk_biz_id: host.biz.id,
      bk_cloud_id: host.cloud_id,
      bk_host_id: host.host_id,
      ip: host.ip,
    };
    emits('ipChange', modelValue.value);
    nextTick(() => {
      inputRef.value.getValue();
    });
  };

  const handleInputError = (value: boolean) => {
    emits('error', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return inputRef.value.getValue().then(() => modelValue.value);
    },
    focus() {
      inputRef.value.focus();
    },
  });
</script>
<style lang="less" scoped>
  .cluster-name-with-selector {
    &:hover {
      :deep(.edit-btn-wraper) {
        display: block;
      }
    }
  }

  .edit-btn-wraper {
    display: none;

    .edit-btn {
      display: flex;
      width: 24px;
      height: 40px;
      align-items: center;

      .edit-btn-inner {
        display: flex;
        width: 24px;
        height: 24px;
        cursor: pointer;
        border-radius: 2px;
        align-items: center;
        justify-content: center;

        .select-icon {
          font-size: 16px;
          color: #979ba5;
        }

        &:hover {
          background: #f0f1f5;

          .select-icon {
            color: #3a84ff;
          }
        }
      }
    }
  }
</style>
