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
  <div
    class="render-host-box"
    @mouseenter="handleControlShowEdit(true)"
    @mouseleave="handleControlShowEdit(false)">
    <div
      class="content-box"
      :class="{'is-empty': !clusterData, 'is-error': Boolean(errorMessage)}">
      <span
        v-if="!localHostIp"
        class="placehold">{{ t('请选择主机') }}</span>
      <span
        v-else
        ref="contentRef"
        v-overflow-tips
        class="content-text">{{ localHostIp }}</span>
      <BkPopover
        v-if="clusterData && showEditIcon"
        :content="t('从业务拓扑选择')"
        placement="top"
        theme="dark">
        <div
          class="edit-btn"
          @click="handleShowIpSelector">
          <div
            class="edit-btn-inner">
            <DbIcon
              class="select-icon"
              type="host-select" />
          </div>
        </div>
      </BkPopover>
      <div
        v-if="errorMessage"
        class="input-error">
        <DbIcon
          v-bk-tooltips="errorMessage"
          type="exclamation-fill" />
      </div>
    </div>
  </div>
  <InstanceSelector
    v-model:is-show="isShowIpSelector"
    :cluster-types="[ClusterTypes.MONGOCLUSTER]"
    :selected="selected"
    :tab-list-config="tabListConfig"
    @change="handleInstanceSelectChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongoDBModel from '@services/model/mongodb/mongodb';
  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type PanelListType,
  } from '@components/instance-selector-new/Index.vue';
  import useValidtor from '@components/render-table/hooks/useValidtor';

  interface Props {
    clusterData?: MongoDBModel
  }

  interface Exposes {
    getValue: () => Promise<{ backup_host: string }>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const contentRef = ref();
  const isShowIpSelector = ref(false);
  const showEditIcon = ref(false);
  const localHostIp = ref<string>('');

  const selected = shallowRef({ [ClusterTypes.MONGOCLUSTER]: [] } as InstanceSelectorValues<MongodbInstanceModel>);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('不能为空'),
    },
  ];

  const tabListConfig = computed(() => ({
    [ClusterTypes.MONGOCLUSTER]: [
      {
        topoConfig: {
          filterClusterId: props.clusterData?.id,
        },
        tableConfig: {
          multiple: false,
        },
      },
    ],
  }) as unknown as Record<ClusterTypes, PanelListType>);

  const {
    message: errorMessage,
    validator,
  } = useValidtor(rules);

  const handleControlShowEdit = (isShow: boolean) => {
    showEditIcon.value = isShow;
  };

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  // 批量选择
  const handleInstanceSelectChange = (data: InstanceSelectorValues<MongodbInstanceModel>) => {
    localHostIp.value = data[ClusterTypes.MONGOCLUSTER][0].ip;
    selected.value[ClusterTypes.MONGOCLUSTER] = data[ClusterTypes.MONGOCLUSTER];
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localHostIp.value)
        .then(() => Promise.resolve({
          backup_host: localHostIp.value,
        }));
    },
  });
</script>
<style lang="less" scoped>
.render-host-box {
  position: relative;
  display: flex;
  width: 100%;
  overflow: hidden;
  align-items: center;

  .content-box {
    position: relative;
    display: flex;
    width: 100%;
    height: 42px;
    align-items: center;
    padding: 0 25px 0 17px;
    overflow: hidden;
    border: solid transparent 1px;

    &:hover {
      cursor: pointer;
      border-color: #a3c5fd;

      .edit-btn-inner {
        background-color: #F0F1F5;
      }
    }

    .placehold {
      color: #C4C6CC;
    }

    .content-text {
      flex: 1;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .edit-btn{
      position: absolute;
      right: 5px;
      z-index: 999;
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
          color: #979BA5;
        }

        &:hover {
          background: #F0F1F5;

          .select-icon {
            color: #3A84FF;
          }

        }
      }
    }

    .input-error {
      position: absolute;
      inset: 0;
      display: flex;
      padding-right: 35px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
      justify-content: flex-end;
    }
  }

  .is-empty {
    background-color: #fafbfd;
    border: none;

    :hover {
      border: none;
    }
  }

  .is-error {
    background-color: #fff1f1;

  }


  .host-input{
    flex: 1;

    :deep(.inner-input) {
      padding-right: 24px;
      background-color: #fff;
      border: solid transparent 1px;

      &:hover {
        background-color: #fafbfd;
        border-color: #a3c5fd;
      }


    }

    &:hover {
      cursor: pointer;
    }
  }


}
</style>
