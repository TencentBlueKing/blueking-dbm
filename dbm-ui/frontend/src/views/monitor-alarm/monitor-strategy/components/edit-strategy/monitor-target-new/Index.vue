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
  <DbFormItem class="monitor-targets-box mt-16">
    <div class="monitor-targets-title mt-16">
      <span class="main-title">{{ t('监控目标') }}</span>
      <span class="sub-title">（子策略必须指定监控目标）</span>
    </div>
    <BkAlert
      class="mt-16"
      theme="warning"
      :title="t('子策略的监控目标优先级高于父策略，匹配到条件的对象将使用子策略的告警配置')" />
    <div class="content-box">
      <div
        v-for="item in flowList"
        :key="item.title"
        class="item-box mt-16"
        :class="{ custom: item.isCustom }">
        <div class="item-box-title">
          {{ item.title }}
        </div>
        <BkSelect
          v-model="item.method"
          :clearable="false"
          collapse-tags
          style="width: 100px">
          <BkOption
            v-for="data in methodList"
            :key="data.id"
            :label="data.name"
            :value="data.id" />
        </BkSelect>
        <div style="width: 100%">
          <BkInput
            v-if="isFuzzyInput(item.method)"
            v-model="item.value"
            clearable
            :placeholder="t('输入通配符匹配模式（如 *test*）')" />
          <template v-else>
            <BkTagInput
              v-if="item.id === MonitorTargetLevel.CLUSTER"
              v-model="item.valueList"
              collapse-tags
              has-delete-icon
              :list="item.selectList"
              :paste-fn="pasteCallback"
              :placeholder="t('请选择')"
              trigger="focus" />
            <BkTagInput
              v-else
              v-model="item.valueList"
              allow-create
              collapse-tags
              has-delete-icon
              :paste-fn="pasteCallback"
              :placeholder="t('请输入')" />
          </template>
        </div>
      </div>
    </div>
  </DbFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';

  import { useGlobalBizs } from '@stores';

  import { MonitorTargetLevel } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  type TargetItem = MonitorPolicyModel['targets'][number];
  type CustomItem = MonitorPolicyModel['custom_conditions'][number];

  type FlowListType = {
    id: MonitorTargetLevel;
    isCustom: boolean;
    isSelect: boolean;
    method: string;
    selectList: {
      label: string;
      value: string;
    }[];
    title: string;
    value: string; // like / not like 运算符使用普通文本输入框
    valueList: string[]; // 其余方法使用select 或 tagInput
  }[];

  interface Exposes {
    getValue: () => any;
    resetValue: () => void;
  }

  interface Props {
    clusterList: SelectItem<string>[];
    customs: CustomItem[];
    isNew: boolean;
    isPromql: boolean;
    targets: TargetItem[];
  }

  const props = defineProps<Props>();

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

  const isFuzzyInput = (method: string) => ['!~-not like', `=~-like`, 'exclude', 'include'].includes(method);

  const initFlowList = () => {
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
            method: methodList.value[0].id,
            selectList: selectClusterList,
            title: t('集群域名'),
            value: '',
            valueList: [],
          },
        ];

    const customeList = props.customs.map((item) => ({
      id: item.key,
      isCustom: true,
      isSelect: false,
      method: getMethod(item.method),
      selectList: [],
      title: item.dimension_name,
      value: isFuzzyInput(item.method) && item.value.length > 0 ? item.value[0] : '',
      valueList: isFuzzyInput(item.method) ? [] : item.value,
    }));
    return [...targetList, ...customeList] as FlowListType;
  };

  // const rules = [
  //   {
  //     message: '',
  //     required: true,
  //     trigger: 'change',
  //     validator: () => {
  //       const clusterItem = flowList.value.find((item) => item.id === MonitorTargetLevel.CLUSTER);
  //       if (clusterItem) {
  //         if (isFuzzyInput(clusterItem.method)) {
  //           return !!clusterItem.value;
  //         } else {
  //           return clusterItem.valueList.length > 0;
  //         }
  //       }
  //       return true;
  //     },
  //   },
  // ];

  const flowList = ref<FlowListType>([]);

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

  const pasteCallback = (text: string) => {
    if (!_.trim(text)) {
      return [];
    }
    return text.split(batchSplitRegex).map((item) => ({
      id: item,
      name: item,
    }));
  };

  defineExpose<Exposes>({
    getValue() {
      const customs = flowList.value
        .filter((item) => item.isCustom)
        .map((row) => ({
          condition: 'and',
          dimension_name: row.title,
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
            (item) =>
              ![MonitorTargetLevel.CLUSTER, MonitorTargetLevel.CUSTOM].includes(item.level as MonitorTargetLevel),
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

    &.bk-form-item.is-error .bk-tag-input-trigger {
      border-color: #ea3636;
      transition: all 0.15s;
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
        width: 100%;
        height: 32px;

        .item-box-title {
          width: 120px;
          padding-right: 8px;
          font-size: 12px;
          text-align: right;
        }

        .content {
          flex: 1;

          .content-custom {
            display: flex;
            width: 100%;

            .condition {
              width: 60px;
              height: 32px;
              line-height: 32px;
              text-align: center;
              border: 1px solid #c4c6cc;
              border-right: none;
            }

            .bk-tag-input {
              flex: 1;
            }
          }
        }
      }
    }
  }
</style>
