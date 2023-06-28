<template>
  <div>
    <IpSelector
      :biz-id="bizId"
      class="mt-12"
      :cloud-info="cloudInfo"
      :disable-host-method="disableHostMethod"
      :disable-tips="data.targetDisk < 1 ? t('请先设置期望容量') : ''"
      :show-view="false"
      @change="handleHostChange">
      <template #submitTips="{ hostList }">
        <I18nT
          keypath="已选n台_共nGB(目标容量:nG)"
          style="font-size: 14px; color: #63656e;"
          tag="span">
          <span
            class="number"
            style="color: #2dcb56;">
            {{ hostList.length }}
          </span>
          <span
            class="number"
            style="color: #3a84ff;">
            {{ calcSelectHostDisk(hostList) }}
          </span>
          <span
            class="number"
            style="color: #63656e;">
            {{ data.targetDisk - data.totalDisk }}
          </span>
        </I18nT>
      </template>
    </IpSelector>
    <div
      v-if="hostTableData.length > 0"
      class="data-preview-table">
      <WithInstanceHostTable
        :biz-id="bizId"
        :data="hostTableData"
        :searchable="false"
        @update:data="handleHostTableChange">
        <template #header>
          <div class="data-preview-header">
            <I18nT keypath="共n台_共nGB">
              <span
                class="number"
                style="color: #3a84ff;">
                {{ hostTableData.length }}
              </span>
              <span
                class="number"
                style="color: #2dcb56;">
                {{ calcSelectHostDisk(hostTableData) }}
              </span>
            </I18nT>
            <I18nT
              v-if="targetMatchReal > 0"
              class="ml-8"
              keypath="较目标容量相差nG">
              <span
                class="number"
                style="color: #ff9c01;">
                {{ targetMatchReal }}
              </span>
            </I18nT>
            <I18nT
              v-if="targetMatchReal < 0"
              class="ml-8"
              keypath="较目标容量超出nG">
              <span
                class="number"
                style="color: #ff9c01;">
                {{ Math.abs(targetMatchReal) }}
              </span>
            </I18nT>
          </div>
        </template>
      </WithInstanceHostTable>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import {
    computed,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { HostDetails } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import WithInstanceHostTable from '@components/cluster-common/big-data-host-table/es-host-table/index.vue';
  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import type { TNodeInfo } from '../../../Index.vue';

  interface Props {
    cloudInfo: {
      id: number,
      name: string
    },
    data: TNodeInfo,
    disableHostMethod?: (params: HostDetails) => string | boolean
  }

  interface Emits {
    (e: 'change', value: TNodeInfo['hostList'], expansionDisk: TNodeInfo['expansionDisk']): void,
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const formatIpDataWidthInstance = (data: HostDetails[]) => data.map(item => ({
    instance_num: 1,
    ...item,
  }));

  const calcSelectHostDisk = (hostList: HostDetails[]) => hostList
    .reduce((result, hostItem) => result + ~~Number(hostItem.bk_disk), 0);


  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const bizId = globalBizsStore.currentBizId;

  const hostTableData = shallowRef<TNodeInfo['hostList']>(props.data.hostList || []);

  // 目标容量和实际容量误差
  const targetMatchReal = computed(() => {
    const {
      totalDisk,
      targetDisk,
      expansionDisk,
    } = props.data;

    const realTargetDisk = totalDisk + expansionDisk;
    return targetDisk - realTargetDisk;
  });

  const handleHostChange = (hostList: HostDetails[]) => {
    hostTableData.value = formatIpDataWidthInstance(hostList);
    emits('change', hostTableData.value, calcSelectHostDisk(hostList));
  };

  const handleHostTableChange = (hostList: TNodeInfo['hostList']) => {
    hostTableData.value = hostList;
    emits('change', hostTableData.value, calcSelectHostDisk(hostList));
  };
</script>

