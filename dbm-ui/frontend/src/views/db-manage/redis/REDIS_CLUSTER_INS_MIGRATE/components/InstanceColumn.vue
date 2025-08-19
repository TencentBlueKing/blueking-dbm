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
    :append-rules="rules"
    field="batchInstance.renderText"
    fixed="left"
    :label="t('目标实例')"
    :loading="isLoading"
    :min-width="300"
    required>
    <template #headAppend>
      <span
        v-bk-tooltips="t('批量选择')"
        class="batch-host-select"
        @click="handleShowSelector">
        <DbIcon type="batch-host-select" />
      </span>
    </template>
    <EditableTextarea
      v-model="modelValue.renderText"
      :placeholder="t('请输入实例，多个实例用分隔符输入')"
      @change="handleInputChange" />
  </EditableColumn>
  <InstanceSelector
    v-model:is-show="showSelector"
    :cluster-types="['RedisInstance']"
    :selected="selectedInstances"
    :tab-list-config="tabListConfig"
    @change="handleInstanceSelectChange" />
</template>
<script lang="ts" setup>
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import { checkInstance } from '@services/source/dbbase';
  import { queryMachineInstancePair } from '@services/source/redisToolbox';

  import { batchSplitRegex, ipPort } from '@common/regex';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  interface Props {
    selected: {
      instance_address: string;
    }[];
    selectedMap: Record<string, boolean>;
    tabListConfig?: Record<string, PanelListType>;
  }

  type Emits = (e: 'batch-edit', list: RedisInstanceModel[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<{
    instances: Record<
      string,
      {
        bk_cloud_id: number;
        bk_host_id: number;
        cluster_id: number;
        cluster_type: string;
        instance_address: string;
        ip: string;
        master_domain: string;
        port: number;
        slave: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port: number;
        };
        spec_config: RedisInstanceModel['spec_config'];
      }
    >;
    renderText: string;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const isLoading = ref(false);
  const showSelector = ref(false);

  const selectedInstances = computed<InstanceSelectorValues<IValue>>(() => ({
    RedisInstance: props.selected.map(
      (item) =>
        ({
          instance_address: item.instance_address,
        }) as IValue,
    ),
  }));
  const selectedCounter = computed(() => _.countBy(props.selected, 'instance_address'));

  const rules = [
    {
      message: t('格式不符合要求'),
      trigger: 'blur',
      validator: (value: string) => !value || value.split(batchSplitRegex).every((item) => ipPort.test(item)),
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const repeats: string[] = [];
        const list = value.split(batchSplitRegex);
        list.forEach((item, index) => {
          if (index !== list.indexOf(item)) {
            repeats.push(item);
          } else if (selectedCounter.value[item] > 1) {
            repeats.push(item);
          }
        });
        return repeats.length ? t('目标实例xx重复', [repeats.join(',')]) : true;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        const notFounds: string[] = [];
        value.split(batchSplitRegex).forEach((item) => {
          if (!props.selectedMap[item]) {
            notFounds.push(item);
          }
        });
        return notFounds.length ? t('目标实例xx不存在', [notFounds.join(',')]) : true;
      },
    },
  ];

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleInputChange = (value: string) => {
    modelValue.value = {
      instances: {},
      renderText: value,
    };
  };

  const handleInstanceSelectChange = (selected: Record<string, RedisInstanceModel[]>) => {
    const list = Object.values(selected).flatMap((selectedList) => selectedList);
    emits('batch-edit', list);
  };

  watch(
    modelValue,
    () => {
      if (modelValue.value.renderText && _.isEmpty(modelValue.value.instances)) {
        isLoading.value = true;
        const masterInstances = modelValue.value.renderText.split(batchSplitRegex);
        Promise.all([
          checkInstance({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            instance_addresses: masterInstances,
          }),
          queryMachineInstancePair({
            instances: masterInstances,
          }),
        ])
          .then(([instanceCheckList, slaveInstanceMap]) => {
            if (instanceCheckList.length) {
              let instances = {};
              instanceCheckList.forEach((item) => {
                const slaveItem = slaveInstanceMap.instances![item.instance_address];
                if (slaveItem) {
                  const slave = {
                    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                    bk_cloud_id: slaveItem.bk_cloud_id,
                    bk_host_id: slaveItem.bk_host_id,
                    ip: slaveItem.ip,
                    port: slaveItem.port,
                  };
                  instances = {
                    ...instances,
                    [item.instance_address]: {
                      bk_host_id: item.bk_host_id,
                      cluster_id: item.cluster_id,
                      cluster_type: item.cluster_type,
                      instance_address: item.instance_address,
                      master_domain: item.master_domain,
                      slave,
                      spec_config: item.spec_config,
                    },
                  };
                }
              });
              modelValue.value.instances = instances;
            }
          })
          .finally(() => {
            isLoading.value = false;
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
</style>
