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
  <div class="targets-box">
    <div class="left-box">
      <div class="item-box">
        <div class="item">
          <span class="top-bar" />
          AND
          <span class="bottom-bar" />
        </div>
      </div>
      <template v-if="flowList.length > 0">
        <div
          v-for="index in flowList.length -1"
          :key="index"
          class="item-box other">
          <div class="item">
            <span class="top-bar" />
            AND
            <span class="bottom-bar" />
          </div>
        </div>
      </template>
    </div>
    <div class="right-box">
      <div class="item-box biz">
        <span class="left-bar" />
        <div class="title-box">
          <BkSelect
            v-model="bizObj.title"
            class="title-select"
            disabled>
            <BkOption
              :label="bizObj.titleList[0].label"
              :value="bizObj.titleList[0].value" />
          </BkSelect>
        </div>
        <div class="content content-other">
          <BkSelect
            v-model="bizObj.value"
            disabled>
            <BkOption
              :label="bizObj.selectList[0].label"
              :value="bizObj.selectList[0].value" />
          </BkSelect>
        </div>
        <div class="operate-box">
          <i
            class="db-icon-plus-fill icon plus"
            :class="{'no-active-icon': !bizObj.activeAdd}"
            @click="() => handleClickPlusItem(-1)" />
        </div>
      </div>
      <div
        v-for="(item, index) in flowList"
        :key="item.title"
        class="item-box other"
        :class="{'custom': item.isCustom}">
        <span class="left-bar" />
        <div class="title-box">
          <BkSelect
            v-if="!item.isCustom"
            v-model="item.title"
            class="title-select"
            :clearable="false"
            @change="(value) => handleTitleChange(index, value)">
            <BkOption
              v-for="data in item.titleList"
              :key="data.value"
              :label="data.label"
              :value="data.value" />
          </BkSelect>
          <span v-else>{{ item.title }}</span>
        </div>
        <div
          class="content"
          :class="{
            'content-other': item.isCustom
          }">
          <BkSelect
            v-if="item.isSelect"
            v-model="item.value"
            :clearable="false"
            collapse-tags
            multiple
            multiple-mode="tag">
            <BkOption
              v-for="data in item.selectList"
              :key="data.value"
              :label="data.label"
              :value="data.value" />
          </BkSelect>
          <div
            v-else
            class="content-custom">
            <span class="condition">{{ signMap[item.value[0]] }}</span>
            <BkInput
              v-model="item.value[1]"
              :placeholder="t('请输入')"
              size="default" />
          </div>
        </div>
        <div class="operate-box">
          <template v-if="!item.isCustom">
            <i
              class="db-icon-plus-fill icon plus"
              :class="{'no-active-icon': !item.activeAdd}"
              @click="() => handleClickPlusItem(index)" />
            <i
              class="db-icon-minus-fill icon minus"
              :class="{'no-active-icon': !item.activeMinus}"
              @click="handleClickMinusItem(index)" />
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
  import { getClusterList, getDbModuleList } from '@services/monitor';

  import { useGlobalBizs } from '@stores';

  import { signMap } from '@components/monitor-rule-check/index.vue';

  type TargetItem = MonitorPolicyModel['targets'][0]

  interface Emits {
    (e: 'change', value: any): void
  }

  interface Exposes {
    getValue: () => any;
    resetValue: () => void;
  }

  interface Props {
    targets: TargetItem[],
    bizsMap: Record<string, string>,
    dbType: string;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const enum TargetType {
    BIZ = 'app_id',
    CUSTER = 'cluster_domain',
    MODULE = 'db_module',
    PLATFORM = 'platform'
  }

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  useRequest(getClusterList, {
    defaultParams: [{
      dbtype: props.dbType,
    }],
    onSuccess: (res) => {
      clusterList.value = res.map(item => ({
        label: item,
        value: item,
      }));
    },
    onError: (e) => {
      console.error('cluster list error:', e);
    },
  });

  useRequest(getDbModuleList, {
    defaultParams: [{
      dbtype: props.dbType,
    }],
    onSuccess: (res) => {
      moduleList.value = res.map(item => ({
        label: item.db_module_name,
        value: item.db_module_id,
      }));
    },
    onError: (e) => {
      console.error('module list error:', e);
    },
  });

  const moduleList = ref<SelectItem[]>([]);
  const clusterList = ref<SelectItem[]>([]);
  const isPlatform = computed(() => props.targets.filter(item => item.level === TargetType.PLATFORM).length > 0);

  const bizObj = computed(() => {
    const bizId = isPlatform ? currentBizId
      : props.targets.filter(item => item.level === TargetType.BIZ)[0].rule.value[0];
    return {
      title: '0',
      titleList: [
        {
          value: '0',
          label: t('业务'),
        },
      ],
      selectList: [
        {
          value: '0',
          label: props.bizsMap[bizId],
        },
      ],
      value: ['0'],
      activeAdd: true,
    };
  });

  const titleListRaw = [
    {
      value: '0',
      label: t('模块'),
    },
    {
      value: '1',
      label: t('集群'),
    },
  ];

  const commonSelectObj = {
    id: TargetType.MODULE, // or cluster
    title: '0',
    titleList: _.cloneDeep(titleListRaw),
    selectList: [],
    isCustom: false,
    isSelect: true,
    activeAdd: true,
    activeMinus: true,
    value: [],
  };

  type SelectObjType = typeof commonSelectObj;

  const flowList = ref(initFlowList());

  watch(flowList, (list) => {
    if (list.length === 0) {
      return;
    }
    const selectCount = list.filter(item => item.isSelect).length;
    if (selectCount === 0) {
      bizObj.value.activeAdd = true;
      return;
    }
    if (selectCount === 2) {
      bizObj.value.activeAdd = false;
    }
    emits('change', list);
  }, {
    immediate: true,
    deep: true,
  });

  function initFlowList() {
    const titles = [TargetType.CUSTER, TargetType.MODULE] as string[];
    let selectCounts = 0;
    const targets = _.cloneDeep(props.targets).reduce((results, item) => {
      if (!([TargetType.BIZ, TargetType.PLATFORM] as string[]).includes(item.level)) {
        if (titles.includes(item.level)) {
          selectCounts = selectCounts + 1;
        }
        results.push(item);
      }
      return results;
    }, [] as TargetItem[]);
    return targets.map((item) => {
      let title = '';
      const isCustom = !titles.includes(item.level);
      if (isCustom) {
        title = item.level;
      } else {
        title = item.level === TargetType.CUSTER ? '1' : '0';
      }
      let titleList = [] as SelectItem[];
      let selectList = [] as SelectItem[];
      if (selectCounts === 1) {
        titleList = _.cloneDeep(titleListRaw);
      } else if (selectCounts === 2) {
        if (title === '1') {
          // 集群
          titleList = [
            {
              value: '1',
              label: t('集群'),
            },
          ];
          selectList = clusterList.value;
        } else {
          titleList = [
            {
              value: '0',
              label: t('模块'),
            },
          ];
          selectList = moduleList.value;
        }
      }

      return {
        id: item.level,
        title,
        isCustom,
        isSelect: !isCustom,
        value: item.rule.value as string | string[],
        titleList,
        selectList,
        activeAdd: selectCounts < 2,
        activeMinus: !isCustom,
      };
    });
  }

  const handleTitleChange = (index:number, value: string) => {
    const isModule = value === '0';
    flowList.value[index].id = isModule ? TargetType.MODULE : TargetType.CUSTER;
    flowList.value[index].selectList = isModule ? moduleList.value : clusterList.value;
  };

  const addFlowSelectItem = (item: SelectObjType) => {
    if (flowList.value.length > 0) {
      flowList.value[0].activeAdd = false;
      flowList.value[0].titleList = [];
      if (flowList.value[0].id === TargetType.MODULE) {
        // 已经有 模块栏
        Object.assign(item, {
          id: TargetType.CUSTER,
          title: '1',
          titleList: [],
          selectList: clusterList.value,
          activeAdd: false,
          activeMinus: true,
        });
        return;
      }
    }
    Object.assign(item, {
      selectList: moduleList.value,
      titleList: _.cloneDeep(titleListRaw),
      activeAdd: false,
      activeMinus: true,
    });
  };

  const handleClickPlusItem = (index: number) => {
    const item = _.cloneDeep(commonSelectObj);
    if (index === -1 && bizObj.value.activeAdd) {
      // 点击业务栏添加
      const selectCount = flowList.value.filter(item => item.isSelect).length;
      if (selectCount === 1) {
        addFlowSelectItem(item);
        flowList.value.splice(1, 0, item);
        return;
      }
      addFlowSelectItem(item);
      flowList.value.unshift(item);
    } else {
      // 点击 集群栏或者模块栏
      addFlowSelectItem(item);
      flowList.value.splice(index + 1, 0, item);
    }
  };

  const handleClickMinusItem = (index: number) => {
    flowList.value.splice(index, 1);
    nextTick(() => {
      bizObj.value.activeAdd = true;
      flowList.value[0].activeAdd  = true;
      flowList.value[0].titleList = _.cloneDeep(titleListRaw);
    });
  };

  defineExpose<Exposes>({
    getValue() {
      const defalutObj =  {
        id: TargetType.BIZ,
        value: isPlatform.value ? [currentBizId]
          : [props.targets.filter(item => item.level === TargetType.BIZ)[0].rule.value[0]],
      };
      return [defalutObj, ...flowList.value];
    },
    resetValue() {
      flowList.value = initFlowList();
    },
  });

</script>
<style lang="less" scoped>
.targets-box {
  display: flex;
  width: 100%;

  .left-box {
    width: 60px;

    .item-box {
      position: relative;
      width: 44px;
      height: 22px;
      margin-top: 20px;
      font-size: 12px;
      line-height: 22px;
      color: #3A84FF;
      text-align: center;
      background: #EDF4FF;
      border-radius: 2px;

      .top-bar {
        position: absolute;
        top: -15px;
        left: 20px;
        width: 0;
        height: 15px;
        border-left: 1px solid #C4C6CC;
      }

      .bottom-bar {
        position: absolute;
        bottom: -15px;
        left: 20px;
        width: 0;
        height: 15px;
        border-left: 1px solid #C4C6CC;
      }
    }

    .other {
      margin-top: 31px;
    }
  }

  .right-box {
    flex: 1;

    .biz {
      .content {
        background-color: #FAFBFD;
      }

    }

    .item-box {
      position: relative;
      display: flex;
      width: 100%;
      height: 32px;
      margin-top: -11px;


      .left-bar {
        position: absolute;
        top: 15px;
        left: -40px;
        width: 40px;
        height: 0;
        border-bottom: 1px solid #C4C6CC;
      }

      .title-box {
        display: flex;
        width: 80px;
        height: 32px;
        background: #FAFBFD;
        align-items: center;
        justify-content: space-between;

        .title-select {
          width: 100%;

          :deep(.bk-input) {
            border-radius: 2px 0 0 2px;
            outline: none;
          }
        }
      }

      .content {
        flex: 1;

        :deep(.bk-input) {
          height: 30px;
          border: none;
          outline: none;
        }

        :deep(.bk-select-tag) {
          width: 100%;
          min-height: 30px;
          overflow: hidden;
          // border: none;
          // outline: none;

          .bk-select-tag-wrapper {
            height: auto;
            max-height: 100px;
            overflow-y: auto;
            // padding: 5px 8px;
          }
        }


        .content-custom {
          display: flex;
          width: 100%;

          .condition {
            width: 60px;
            height: 30px;
            line-height: 30px;
            text-align: center;
            border-right: 1px solid #C4C6CC;
          }
        }
      }

      .content-other {
        border: 1px solid #C4C6CC;
        border-left: none;
      }

      .operate-box {
        display: flex;
        width: 85px;
        align-items: center;
        padding-left: 12px;

        .plus {
          margin-right: 12px;
        }

        .icon {
          font-size: 18px;
          cursor: pointer;
        }

        .active-icon {
          color: #979BA5;
        }

        .no-active-icon {
          color: #C4C6CC;
        }
      }
    }

    .other {
      margin-top: 21px;
    }

    .custom {
      .title-box {
        padding: 0;
        background: #F5F7FA;
        border: none;
        justify-content: center;
        border-right: 1px solid #C4C6CC;

        span {
          font-size: 12px;
        }
      }
    }
  }
}
</style>
