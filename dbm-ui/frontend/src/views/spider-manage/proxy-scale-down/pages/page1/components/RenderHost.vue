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
    <RenderText
      v-if="selectedIpList"
      ref="textRef"
      class="ip-box"
      :data="selectedIpList"
      @click="handleIpTextClick">
      <template #content="{ data: ipData }">
        <div class="ip-content">
          <div class="ip-text">{{ ipData }}</div>
          <DbIcon
            class="delete-icon"
            type="delete-fill"
            @click.stop="handleIpDelete" />
        </div>
      </template>
    </RenderText>
    <TableEditSelect
      v-else
      ref="selectRef"
      v-model="localValue"
      :disabled="!data?.clusterId"
      :filterable="false"
      :list="selectList"
      :placeholder="t('请选择')"
      :rules="rules"
      @change="(value) => handleChange(value as string)" />
  </div>
  <InstanceSelector
    v-model:is-show="isShowInstanceSelecotr"
    :cluster-types="[ClusterTypes.TENDBCLUSTER]"
    :selected="selected"
    :tab-list-config="tabListConfig"
    @change="handleInstancesChange" />
</template>

<script lang="ts">
  export enum HostSelectType {
    AUTO = 'auto',
    MANUAL = 'manual',
  }
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
  import TableEditSelect from '@components/render-table/columns/select/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { NodeType } from './RenderNodeType.vue';
  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow;
  }

  interface Emits {
    (e: 'type-change', value: string): void;
    (e: 'num-change', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const selectRef = ref();
  const textRef = ref();
  const isShowInstanceSelecotr = ref(false);
  const localValue = ref(props.data?.hostSelectType ? props.data?.hostSelectType : HostSelectType.AUTO);

  const selected = shallowRef({ [ClusterTypes.TENDBCLUSTER]: [] } as InstanceSelectorValues<IValue>);

  const selectList = [
    {
      label: t('自动匹配'),
      value: HostSelectType.AUTO,
    },
    {
      label: t('手动选择'),
      value: HostSelectType.MANUAL,
    },
  ];

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('请选择节点类型'),
    },
  ];

  const tabListConfig = computed(() => {
    const isMater = props.data?.nodeType === NodeType.MASTER;
    return {
      [ClusterTypes.TENDBCLUSTER]: [
        {
          name: t('目标从库'),
          topoConfig: {
            filterClusterId: props.data!.clusterId,
          },
          tableConfig: {
            firsrColumn: {
              label: isMater ? t('Master 主机') : t('Slave 主机'),
              field: 'ip',
              role: isMater ? 'spider_master' : 'spider_slave',
            },
          },
        },
        {
          tableConfig: {
            firsrColumn: {
              label: isMater ? t('Master 主机') : t('Slave 主机'),
              field: 'ip',
              role: isMater ? 'spider_master' : 'spider_slave',
            },
          },
        },
      ],
    } as unknown as Record<ClusterTypes, PanelListType>;
  });

  const selectedIpList = computed(() => selected.value[ClusterTypes.TENDBCLUSTER].map((item) => item.ip).join('，'));

  const handleIpDelete = () => {
    selected.value[ClusterTypes.TENDBCLUSTER] = [];
    emits('num-change', 0);
  };

  const handleChange = (value: string) => {
    localValue.value = value as HostSelectType;
    if (value === HostSelectType.MANUAL) {
      isShowInstanceSelecotr.value = true;
    }
    emits('type-change', value);
  };

  const handleInstancesChange = (selectedValues: InstanceSelectorValues<IValue>) => {
    selected.value = selectedValues;
    emits('num-change', selected.value[ClusterTypes.TENDBCLUSTER].length);
  };

  const handleIpTextClick = () => {
    isShowInstanceSelecotr.value = true;
  };

  defineExpose<Exposes>({
    getValue() {
      const formatHost = (host: IValue) => ({
        ip: host.ip,
        bk_host_id: host.bk_host_id,
        bk_cloud_id: host.bk_cloud_id,
        bk_biz_id: currentBizId,
      });
      return selectRef.value.getValue().then(() => ({
        spider_reduced_hosts: selected.value[ClusterTypes.TENDBCLUSTER].map((item) => formatHost(item)),
      }));
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

    .ip-box {
      cursor: pointer;

      .ip-content {
        display: flex;
        align-items: center;

        .ip-text {
          flex: 1;
        }

        .delete-icon {
          color: #979ba5;
          display: none;
        }
      }

      &:hover {
        .delete-icon {
          display: inline-block;
        }
      }
    }
  }
</style>
