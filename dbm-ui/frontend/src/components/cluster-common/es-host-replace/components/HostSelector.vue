<template>
  <div class="es-cluster-replace-host-selector">
    <div
      v-show="data.hostList.length > 0"
      class="result-value">
      <div>
        <div
          v-for="hostItem in data.hostList"
          :key="hostItem.host_id"
          class="data-row">
          <div>{{ hostItem.ip }}</div>
          <div class="data-row-edit-instance">
            <EditHostInstance
              :model-value="hostItem.instance_num"
              @change="value => handleInstanceNumChange(value, hostItem)" />
          </div>
          <div
            class="data-row-remve-btn"
            @click="handleRemoveHost(hostItem)">
            <DbIcon type="close" />
          </div>
        </div>
      </div>
    </div>
    <div
      v-show="data.hostList.length < 1"
      class="action-box">
      <IpSelector
        v-model:show-dialog="isShowIpSelector"
        :biz-id="currentBizId"
        :cloud-info="cloudInfo"
        :disable-dialog-submit-method="disableDialogSubmitMethod"
        :disable-host-method="disableHostMethod"
        :show-view="false"
        @change="handleHostChange">
        <template #submitTips="{ hostList: resultHostList }">
          <I18nT
            keypath="需n台_已选n台"
            style="font-size: 14px; color: #63656e;"
            tag="span">
            <span
              class="number"
              style="color: #2dcb56;">
              {{ data.nodeList.length }}
            </span>
            <span
              class="number"
              style="color: #3a84ff;">
              {{ resultHostList.length }}
            </span>
          </I18nT>
        </template>
      </IpSelector>
    </div>
    <Teleport :to="`#${placehoderId}`">
      <span
        v-if="data.hostList.length > 0"
        class="ip-edit-btn"
        @click="handleShowIpSelector">
        <DbIcon type="edit" />
      </span>
    </Teleport>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { HostDetails } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import EditHostInstance from '@components/cluster-common/big-data-host-table/es-host-table/components/EditHostInstance.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import type { TReplaceNode } from '../Index.vue';

  interface Props {
    data: TReplaceNode,
    placehoderId: string,
    disableHostMethod?: (params: HostDetails) => string | boolean
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<TReplaceNode['hostList']>({
    required: true,
  });

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const formatIpDataWidthInstance = (data: HostDetails[]) => data.map(item => ({
    instance_num: 1,
    ...item,
  }));

  const cloudInfo = computed(() => {
    const [firstItem] = props.data.nodeList;
    if (firstItem) {
      return {
        id: firstItem.bk_cloud_id,
        name: firstItem.bk_cloud_name,
      };
    }
    return undefined;
  });

  const disableDialogSubmitMethod = (hostList: HostDetails[]) => (
    hostList.length === props.data.nodeList.length
      ? false
      : t('需n台', { n: props.data.nodeList.length })
  );

  const isShowIpSelector = ref(false);

  // 选择IP
  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  // 添加新IP
  const handleHostChange = (hostList: HostDetails[]) => {
    modelValue.value = formatIpDataWidthInstance(hostList);
  };

  const handleInstanceNumChange = (value: number, hostData: Props['data']['hostList'][0]) => {
    modelValue.value = modelValue.value.reduce((result, item) => {
      if (item.host_id === hostData.host_id) {
        result.push({
          ...item,
          instance_num: Number(value),
        });
      } else {
        result.push(item);
      }
      return result;
    }, [] as Props['data']['hostList']);
  };

  // 移除替换的主机
  const handleRemoveHost = (host: Props['data']['hostList'][0]) => {
    modelValue.value = modelValue.value.reduce((result, item) => {
      if (item.host_id !== host.host_id) {
        result.push(item);
      }
      return result;
    }, [] as Props['data']['hostList']);
  };
</script>
<style lang="less">
  .es-cluster-replace-host-selector {
    font-size: 12px;
    color: #63656E;

    .result-value{
      height: 100%;

      .data-row{
        display: flex;
        height: 40px;
        align-items: center;
        padding-left: 16px;

        & ~ .data-row{
          border-top: 1px solid #DCDEE5;
        }

        &:hover{
          .data-row-remve-btn{
            opacity: 100%;
          }
        }
      }

      .data-row-remve-btn{
        display: flex;
        width: 52px;
        height: 100%;
        font-size: 16px;
        color: #3A84FF;
        cursor: pointer;
        opacity: 0%;
        transition: all .15s;
        justify-content: center;
        align-items: center;
      }

      .data-row-edit-instance{
        width: 100px;
        margin-left: auto;
        text-align: right;
      }

      .es-cluster-node-edit-host-instance{
        .bk-input--text{
          text-align: right;
        }
      }
    }

    .action-box{
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }
  }
</style>
