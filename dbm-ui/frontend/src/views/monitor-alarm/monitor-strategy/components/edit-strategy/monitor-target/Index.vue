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
  <DbFormItem
    ref="formItem"
    class="monitor-targets-box mt-16 mb-16"
    property="targets"
    :rules="rules">
    <div class="monitor-targets-title mt-16">
      <span class="main-title">{{ t('监控目标') }}</span>
      <span class="sub-title">（{{ t('子策略必须指定监控目标') }}）</span>
    </div>
    <BkAlert
      class="mt-16"
      theme="warning"
      :title="t('子策略的监控目标优先级高于父策略，匹配到条件的对象将使用子策略的告警配置')" />
    <div class="content-box">
      <div
        v-for="item in flowList"
        :key="item.id"
        class="item-box mt-16"
        :class="{ custom: item.isCustom }">
        <div class="item-box-title">
          {{ item.isCustom ? customTitleMap[item.id] : item.title }}
        </div>
        <BkSelect
          v-model="item.method"
          class="method-select"
          :clearable="false"
          collapse-tags
          style="width: 100px"
          @change="handleChange">
          <BkOption
            v-for="data in methodList"
            :key="data.id"
            :label="data.name"
            :value="data.id" />
        </BkSelect>
        <div style="flex: 1">
          <BkInput
            v-if="isFuzzyInput(item.method)"
            v-model="item.value"
            clearable
            :placeholder="t('输入通配符匹配模式（如 *test*），留空表示匹配全部')"
            @change="handleChange" />
          <template v-else>
            <DbTagInput
              v-if="item.id === MonitorTargetLevel.CLUSTER"
              v-model="item.valueList"
              :content-width="500"
              :list="item.selectList"
              mode="only-candidate"
              multiple
              :placeholder="t('留空表示匹配全部')"
              @change="handleChange" />
            <DbTagInput
              v-else
              v-model="item.valueList"
              allow-create
              mode="free-input"
              multiple
              :placeholder="t('留空表示匹配全部')"
              @change="handleChange" />
          </template>
        </div>
        <!-- <BkButton
          v-if="isCustomExist"
          class="minus-btn ml-4"
          :disabled="displayFlowList.length === 1"
          text
          @click="() => handleClickMinusItem(item.realIndex)">
          <DbIcon type="minus-fill" />
        </BkButton> -->
      </div>
    </div>
  </DbFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

  import { useGlobalBizs } from '@stores';

  import { MonitorTargetLevel } from '@common/const';

  type TargetItem = MonitorPolicyModel['targets'][number];
  type CustomItem = MonitorPolicyModel['custom_conditions'][number];

  type FlowListType = {
    id: MonitorTargetLevel;
    isCustom: boolean;
    isSelect: boolean;
    // isShow: boolean;
    method: string;
    // realIndex: number;
    selectList: {
      id: string;
      name: string;
    }[];
    title: string;
    value: string; // like / not like 运算符使用普通文本输入框
    valueList: string[]; // 其余方法使用select 或 tagInput
  }[];

  interface Props {
    clusterList: SelectItem<string>[];
    customs: CustomItem[];
    isNew: boolean;
    isPromql: boolean;
    targets: TargetItem[];
  }

  type Emits = (e: 'change') => void;

  interface Exposes {
    getValue: () => any;
    resetValue: () => void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const commonOptions = [
    { id: 'eq', name: 'in' },
    { id: 'neq', name: 'not in' },
    { id: 'include', name: 'like' },
    { id: 'exclude', name: 'not like' },
    { id: 'reg', name: 'regex' },
    { id: 'nreg', name: 'nregex' },
  ];
  const promqlOptions = [
    { id: '=', name: 'in' },
    { id: '!=', name: 'not in' },
    { id: '=~', name: 'like' },
    { id: '!~', name: 'not like' },
    { id: '=~', name: 'regex' },
    { id: '!~', name: 'nregex' },
  ];
  const promqlOriginOptionMap = Object.fromEntries(promqlOptions.map((item) => [item.id, item.name]));
  const promqlDisplayOptionMap = Object.fromEntries(promqlOptions.map((item) => [`${item.id}-${item.name}`, item.id]));

  const customTitleMap: Record<string, string> = {
    consumergroup: t('消费组'),
    topic: 'Topic',
  };

  const isFuzzyInput = (method: string) =>
    ['!~-not like', '!~-nregex', `=~-like`, '=~-regex', 'exclude', 'include', 'nreg', 'reg'].includes(method);

  const initFlowList = (): FlowListType => {
    const clusterDomainItem = props.targets.find((item) => item.level === MonitorTargetLevel.CLUSTER);
    const getMethod = (originMethod: TargetItem['rule']['method']) => {
      if (props.isPromql) {
        const methodId = originMethod;
        const methodName = promqlOriginOptionMap[methodId];
        return `${methodId}-${methodName}`;
      }
      return originMethod;
    };

    const selectClusterList = props.clusterList.map((item) => ({
      id: item.value,
      name: item.label,
    }));
    const targetList = clusterDomainItem
      ? [
          {
            id: MonitorTargetLevel.CLUSTER,
            isCustom: false,
            isSelect: true,
            // isShow: true,
            method: getMethod(clusterDomainItem.rule.method),
            selectList: selectClusterList,
            title: t('集群域名'),
            value: isFuzzyInput(getMethod(clusterDomainItem.rule.method))
              ? clusterDomainItem.rule.value?.[0] || ''
              : '',
            valueList: isFuzzyInput(getMethod(clusterDomainItem.rule.method)) ? [] : clusterDomainItem.rule.value,
          },
        ]
      : [
          {
            id: MonitorTargetLevel.CLUSTER,
            isCustom: false,
            isSelect: true,
            // isShow: true,
            method: methodList.value[0].id,
            selectList: selectClusterList,
            title: t('集群域名'),
            value: '',
            valueList: [],
          },
        ];

    const customList = props.customs.map((item) => ({
      id: item.key as MonitorTargetLevel,
      isCustom: true,
      isSelect: false,
      // isShow: true,
      method: getMethod(item.method),
      selectList: [],
      title: item.dimension_name,
      value: isFuzzyInput(item.method) && item.value.length > 0 ? item.value[0] : '',
      valueList: isFuzzyInput(item.method) ? [] : item.value,
    }));
    // return [...targetList, ...customeList].map((item, index) => Object.assign({}, item, { realIndex: index }));
    return [...targetList, ...customList];
  };

  const rules = [
    {
      message: t('至少填写一个条件，子策略需通过条件匹配特定对象。'),
      required: true,
      trigger: 'change',
      validator: () => {
        return flowList.value.some((item) => {
          if (isFuzzyInput(item.method)) {
            return !!item.value;
          } else {
            return item.valueList.length > 0;
          }
        });
      },
    },
  ];

  const formItemRef = useTemplateRef('formItem');

  const flowList = ref<FlowListType>([]);

  // const displayFlowList = computed(() => flowList.value.filter((item) => item.isShow));
  // const isCustomExist = computed(() => props.customs.length > 0);
  const methodList = computed(() =>
    props.isPromql ? promqlOptions.map((item) => ({ id: `${item.id}-${item.name}`, name: item.name })) : commonOptions,
  );

  watch(
    () => props.clusterList,
    () => {
      flowList.value = initFlowList();
    },
    {
      immediate: true,
    },
  );

  const handleChange = () => {
    formItemRef.value!.validate();
    emits('change');
  };

  // const handleClickMinusItem = (index: number) => {
  //   flowList.value[index].isShow = false;

  //   const flowItem = flowList.value[index];
  //   if (flowItem.value || flowItem.valueList.length > 0) {
  //     handleChange();
  //   }
  // };

  const getFinalValue = () => {
    const customs = flowList.value
      .filter((item) => item.isCustom)
      .map((row) => ({
        condition: 'and',
        dimension_name: /[\u4e00-\u9fa5]/.test(row.title) ? row.id : row.title,
        key: row.id,
        method: props.isPromql ? promqlDisplayOptionMap[row.method] : row.method,
        value: isFuzzyInput(row.method) ? [row.value] : row.valueList,
      }));

    const defalutTarget = props.isNew
      ? [
          {
            level: MonitorTargetLevel.BIZ,
            rule: {
              key: MonitorTargetLevel.BIZ,
              method: props.isPromql ? promqlOptions[0].id : commonOptions[0].id,
              value: [currentBizId],
            },
          },
        ]
      : props.targets.filter(
          (item) => ![MonitorTargetLevel.CLUSTER, MonitorTargetLevel.CUSTOM].includes(item.level as MonitorTargetLevel),
        );
    const targetList = flowList.value
      .filter((item) => !item.isCustom)
      .map((row) => ({
        level: row.id,
        rule: {
          key: row.id,
          method: props.isPromql ? promqlDisplayOptionMap[row.method] : row.method,
          value: isFuzzyInput(row.method) ? [row.value] : row.valueList,
        },
      }));
    const targets = [
      ...defalutTarget,
      ...targetList,
      ...customs.map((customsItem) => ({
        level: MonitorTargetLevel.CUSTOM,
        rule: {
          key: customsItem.key,
          method: customsItem.method,
          value: customsItem.value,
        },
      })),
    ];
    return {
      custom_conditions: customs,
      targets,
    };
  };

  defineExpose<Exposes>({
    getValue() {
      return getFinalValue();
    },
    resetValue() {
      flowList.value = initFlowList();
    },
  });
</script>
<style lang="less">
  .monitor-targets-box {
    width: 100%;
    border-top: 1px solid rgb(234 235 240);

    &.bk-form-item.is-error {
      .db-tag-input-panel {
        border-color: #ea3636;
        transition: all 0.15s;
      }

      .method-select {
        .bk-input {
          border-color: #c4c6cc;
        }
      }
    }

    .bk-form-content {
      .bk-form-error {
        left: 200px;
      }
    }

    .monitor-targets-title {
      .main-title {
        font-weight: bolder;
        color: #313238;
      }

      .sub-title {
        font-size: 12px;
      }
    }

    .content-box {
      margin-bottom: 8px;

      .item-box {
        position: relative;
        display: flex;
        align-items: center;
        width: 100%;
        height: 32px;

        .item-box-title {
          width: 100px;
          padding-right: 8px;
          font-size: 12px;
          text-align: right;
        }

        .minus-btn {
          font-size: 18px;
        }
      }
    }
  }
</style>
