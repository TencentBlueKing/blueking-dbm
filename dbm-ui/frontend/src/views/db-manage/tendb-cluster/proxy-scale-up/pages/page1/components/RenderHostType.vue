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
  <div class="render-switch-box">
    <TableEditSelect
      ref="selectRef"
      v-model="localValue"
      disabled
      :list="selectList"
      :rules="rules"
      :validate-after-select="false"
      @change="(value) => handleChange(value as string)">
      <template
        v-if="localValue === HostSwicthType.MANUAL"
        #trigger>
        <div class="ip-list-main">
          <TextOverflowLayout :key="ipListDisplay">
            <span>{{ ipList.length > 0 ? ipListDisplay : t('请选择主机') }}</span>
          </TextOverflowLayout>
        </div>
      </template>
    </TableEditSelect>
  </div>
  <IpSelector
    v-model:show-dialog="showIpSelector"
    :biz-id="bizId"
    button-text=""
    :data="selectedIpList"
    :is-cloud-area-restrictions="false"
    :panel-list="['staticTopo', 'manualInput']"
    service-mode="all"
    :show-view="false"
    @change="handleChangeIP" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { HostInfo } from '@services/types';

  import IpSelector from '@components/ip-selector/IpSelector.vue';
  import TableEditSelect from '@components/render-table/columns/select/index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface Props {
    data?: string;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  interface Emits {
    (e: 'change', value: string): void;
    (e: 'ip-list-change', value: string[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: HostSwicthType.AUTO,
  });

  const emits = defineEmits<Emits>();

  enum HostSwicthType {
    AUTO = 'auto',
    MANUAL = 'manual',
  }

  const { t } = useI18n();

  const selectRef = ref<InstanceType<typeof TableEditSelect>>();
  const localValue = ref(props.data);
  const showIpSelector = ref(false);

  const selectedIpList = shallowRef<HostInfo[]>([]);

  const ipList = computed(() => selectedIpList.value.map((item) => item.ip));

  const ipListDisplay = computed(() => ipList.value.join(','));

  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  const rules = [
    {
      validator: (value: string) => {
        if (value === HostSwicthType.MANUAL) {
          return selectedIpList.value.length > 0;
        }
        return true;
      },
      message: t('请选择主机'),
    },
  ];

  const selectList = [
    {
      value: HostSwicthType.AUTO,
      label: t('资源池自动匹配'),
    },
    {
      value: HostSwicthType.MANUAL,
      label: t('资源池手动选择'),
    },
  ];

  // const handleShowIpSelector = () => {
  //   showIpSelector.value = true;
  //   setTimeout(() => {
  //     selectRef.value!.hidePopover();
  //   })
  // }

  const handleChangeIP = (ipList: HostInfo[]) => {
    selectedIpList.value = ipList;
    emits(
      'ip-list-change',
      ipList.map((item) => item.ip),
    );
  };

  const handleChange = (value: string) => {
    localValue.value = value as HostSwicthType;
    if (value === HostSwicthType.MANUAL) {
      showIpSelector.value = true;
    }
    emits('change', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return selectRef.value!.getValue().then(() => localValue.value);
    },
  });
</script>
<style lang="less" scoped>
  .render-switch-box {
    padding: 0;
    color: #63656e;

    :deep(.bk-input--text) {
      border: none;
      outline: none;
    }

    .ip-list-main {
      padding-left: 16px;
    }
  }
</style>
