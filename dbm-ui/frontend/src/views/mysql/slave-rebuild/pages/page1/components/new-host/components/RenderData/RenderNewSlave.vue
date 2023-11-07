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
    <BkPopover
      :is-show="isShowOverflowTip"
      placement="top"
      :popover-delay="0"
      theme="light"
      trigger="manual">
      <div
        class="content-box"
        :class="{'is-empty': !oldSlave, 'is-error': Boolean(errorMessage)}">
        <span
          v-if="!localHostData"
          class="placehold">{{ t('请选择主机') }}</span>
        <span
          v-else
          ref="contentRef"
          class="content-text">{{ localHostData.ip }}</span>
        <BkPopover
          v-if="!!oldSlave && showEditIcon"
          :content="t('从业务拓扑选择')"
          placement="top"
          theme="dark">
          <div
            class="edit-btn"
            @click="handleShowIpSelector">
            <div class="edit-btn-inner">
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
      <template #content>
        {{ localHostData?.ip }}}
      </template>
    </BkPopover>
  </div>
  <IpSelector
    v-if="oldSlave"
    v-model:show-dialog="isShowIpSelector"
    :biz-id="currentBizId"
    button-text=""
    :cloud-info="{
      id: oldSlave.bkCloudId,
      name: oldSlave.bkCloudName,
    }"
    service-mode="all"
    :show-view="false"
    single-host-select
    @change="handleHostChange" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { HostDetails } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import type { IDataRow } from './Row.vue';
  import useValidtor from './useValidtor';

  interface Props {
    oldSlave?: IDataRow['oldSlave']
  }

  interface Exposes {
    getValue: () => Promise<{
      new_slave: {
        bk_host_id: number,
        ip: string,
        bk_cloud_id: number
      }
    }>
  }

  defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const contentRef = ref();
  const isShowIpSelector = ref(false);
  const showEditIcon = ref(false);
  const isOverflow = ref(false);

  const localHostData = shallowRef<HostDetails>();

  const isShowOverflowTip = computed(() => isOverflow.value && showEditIcon.value);

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('新从库主机不能为空'),
    },
  ];

  const {
    message: errorMessage,
    validator,
  } = useValidtor(rules);

  watch(localHostData, () => {
    if (localHostData.value) {
      validator(localHostData.value).finally(() => {
        setTimeout(() => {
          isOverflow.value =  contentRef.value.clientWidth < contentRef.value.scrollWidth;
        });
      });
    }
  }, {
    deep: true,
  });

  const handleControlShowEdit = (isShow: boolean) => {
    showEditIcon.value = isShow;
  };

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  const handleHostChange = (hostList: HostDetails[]) => {
    [localHostData.value] = hostList;
  };

  defineExpose<Exposes>({
    getValue() {
      return validator(localHostData.value)
        .then(() => {
          if (!localHostData.value) {
            return Promise.reject();
          }
          return {
            new_slave: {
              bk_biz_id: localHostData.value.biz.id,
              bk_cloud_id: localHostData.value.cloud_id,
              bk_host_id: localHostData.value.host_id,
              ip: localHostData.value.ip,
            },
          };
        });
    },
  });
</script>
<style lang="less" scoped>
.render-host-box {
  position: relative;
  display: flex;
  align-items: center;
  overflow: hidden;

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
