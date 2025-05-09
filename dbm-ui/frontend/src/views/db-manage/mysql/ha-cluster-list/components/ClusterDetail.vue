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
    v-bkloading="{ loading: isLoading }"
    class="cluster-detail-dialog-mode">
    <DialogModeHeader
      v-if="data"
      :data="data">
      <BkButton
        class="ml-8"
        size="small">
        {{ t('授权') }}
      </BkButton>
      <BkButton
        class="ml-8"
        size="small">
        Webconsole
      </BkButton>
      <BkButton
        class="ml-8"
        size="small">
        {{ t('导出数据') }}
      </BkButton>
      <BkButton
        v-bk-tooltips="t('复制')"
        class="ml-8"
        size="small"
        style="padding: 0 6px">
        <DbIcon type="copy-2" />
      </BkButton>
      <a style="margin-left: auto">
        <DbIcon
          class="mr-4"
          type="link" />
        {{ t('新窗口打开') }}
      </a>
    </DialogModeHeader>
    <BkTab
      v-model:active="activePanelKey"
      class="content-tabs"
      type="card-tab">
      <BkTabPanel
        v-if="checkDbConsole('mysql.haClusterList.clusterTopo')"
        :label="t('集群拓扑')"
        name="topo" />
      <BkTabPanel
        :label="t('集群主机')"
        name="hostList" />
      <BkTabPanel
        v-if="checkDbConsole('mysql.haClusterList.basicInfo')"
        :label="t('基本信息')"
        name="info" />
      <BkTabPanel
        v-if="checkDbConsole('mysql.haClusterList.changeLog')"
        :label="t('变更记录')"
        name="record" />
      <BkTabPanel
        v-for="item in monitorPanelList"
        :key="item.name"
        :label="item.label"
        :name="item.name" />
    </BkTab>
    <div class="content-wrapper">
      <ClusterTopo
        v-if="activePanelKey === 'topo'"
        :id="clusterId"
        :cluster-type="ClusterTypes.TENDBHA"
        :db-type="DBTypes.MYSQL" />
      <HostList
        v-if="activePanelKey === 'hostList'"
        :cluster-id="clusterId"
        :cluster-type="ClusterTypes.TENDBHA" />
      <ClusterBaseInfo
        v-if="activePanelKey === 'info' && data"
        :data="data" />
      <ClusterEventChange
        v-if="activePanelKey === 'record'"
        :id="clusterId" />
      <MonitorDashboard
        v-if="activePanelKey === activePanel?.name"
        :url="activePanel?.link" />
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getMonitorUrls } from '@services/source/monitorGrafana';
  import { getTendbhaDetail } from '@services/source/tendbha';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes } from '@common/const';

  import ClusterTopo from '@views/db-manage/common/cluster-details/ClusterTopo.vue';
  import DialogModeHeader from '@/views/db-manage/common/cluster-details/DisplayBox.vue';
  import HostList from '@/views/db-manage/common/cluster-details/components/HostList.vue';
  import ClusterEventChange from '@views/db-manage/common/cluster-event-change/EventChange.vue';
  import MonitorDashboard from '@views/db-manage/common/cluster-monitor/MonitorDashboard.vue';

  import { checkDbConsole } from '@utils';

  import ClusterBaseInfo from './ClusterBaseInfo.vue';

  interface Props {
    clusterId: number;
  }
  interface PanelItem {
    label: string;
    link: string;
    name: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const activePanelKey = ref('topo');
  const data = ref<TendbhaModel>();

  const monitorPanelList = ref<PanelItem[]>([]);

  const activePanel = computed(() => {
    const targetPanel = monitorPanelList.value.find((item) => item.name === activePanelKey.value);
    return targetPanel;
  });

  const { loading: isLoading, run: fetchResourceDetails } = useRequest(getTendbhaDetail, {
    manual: true,
    onSuccess(result: TendbhaModel) {
      data.value = result;
    },
  });

  const { run: runGetMonitorUrls } = useRequest(getMonitorUrls, {
    manual: true,
    onSuccess(res) {
      if (res.urls.length > 0) {
        monitorPanelList.value = res.urls.map((item) => ({
          label: item.view,
          link: item.url,
          name: item.view,
        }));
      }
    },
  });

  watch(
    () => props.clusterId,
    () => {
      if (!props.clusterId) {
        return;
      }
      fetchResourceDetails({
        id: props.clusterId,
      });
      runGetMonitorUrls({
        bk_biz_id: currentBizId,
        cluster_id: props.clusterId,
        cluster_type: ClusterTypes.TENDBHA,
      });
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    background: #fff;

    .content-tabs {
      .bk-tab-content {
        padding: 0;
      }
    }

    .content-wrapper {
      height: calc(100vh - 168px);
      padding: 0 24px;
      overflow: auto;
    }
  }
</style>
