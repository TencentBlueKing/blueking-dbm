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
  <BkDialog
    class="mongo-access-entry"
    :is-show="isShow"
    :quick-close="false"
    :title="t('获取访问方式')"
    width="1000"
    @closed="handleClose">
    <div class="copy-info">
      <BkButton
        text
        theme="primary"
        @click="handleCopyAll">
        {{ t('复制信息') }}
      </BkButton>
    </div>
    <BkLoading :loading="clbLoading || passwordLoading">
      <div class="mongo-access-entry-content">
        <div
          v-for="(item, index) in dataList"
          :key="index"
          class="mongo-access-entry-item">
          <div class="mongo-access-entry-item-label">
            {{ item.label }}
            <BkTag
              v-if="item.tag"
              class="ml-4"
              size="small"
              theme="info">
              {{ item.tag }}
            </BkTag>
            ：
          </div>
          <div class="mongo-access-entry-item-value">
            <div>
              <span>{{ item.value || '--' }}</span>
              <BkButton
                v-if="item.password && isPasswordExits"
                class="ml-4"
                text
                theme="primary"
                @click="() => handlePasswordShow(item.type)">
                <DbIcon type="visible1" />
              </BkButton>
              <BkButton
                v-bk-tooltips="t('复制xxx', [item.label])"
                class="copy-btn"
                text
                theme="primary"
                @click="handleCopy(item.value, item.type)">
                <DbIcon type="copy" />
              </BkButton>
            </div>
          </div>
        </div>
      </div>
      <div
        v-if="entryInfo"
        class="cluster-clb-main">
        <div class="main-title">
          {{ entryInfo.title }}
        </div>
        <div
          v-for="(item, index) in entryInfo.list"
          :key="index"
          class="item-box">
          <div class="item-title">{{ item.title }}：</div>
          <div class="item-content">
            <span
              v-overflow-tips
              class="text-overflow">
              {{ item.value }}
            </span>
            <DbIcon
              v-bk-tooltips="t('复制n', { n: item.title })"
              class="copy-btn"
              type="copy"
              @click="() => execCopy(item.value)" />
          </div>
        </div>
      </div>
    </BkLoading>
    <template #footer>
      <BkButton @click="handleClose">
        {{ t('关闭') }}
      </BkButton>
    </template>
  </BkDialog>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterEntryDetailModel, {
    type ClbPolarisTargetDetails,
  } from '@services/model/cluster-entry/cluster-entry-details';
  import MongodbModel from '@services/model/mongodb/mongodb';
  import MongodbDetailModel from '@services/model/mongodb/mongodb-detail';
  import { getClusterEntries } from '@services/source/clusterEntry';
  import { getPassword } from '@services/source/mongodb';

  import { compareVersions, execCopy } from '@utils';

  interface Props {
    data: MongodbModel | MongodbDetailModel;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const dataList = ref<
    {
      label: string;
      password?: boolean;
      tag?: string;
      type: string;
      value: string;
    }[]
  >([]);

  const isMongosPasswordShow = ref(false);
  const isAccessPasswordShow = ref(false);
  const isAccessClbPasswordShow = ref(false);

  const entryInfo = shallowRef<{
    list: {
      shareLink?: string;
      title: string;
      value: string;
    }[];
    title: string;
  }>();

  const isPasswordExits = computed(() => passwordData.value && passwordData.value.password);

  const getFormatPassword = (isPasswordShow: boolean) => {
    if (isPasswordExits.value) {
      return `mongodb://${passwordData.value!.username}:${isPasswordShow ? passwordData.value!.password : '******'}@`;
    }
    return 'mongodb://{username}:{password}@';
  };

  const getEntryAccess = (data: Props['data'], entryDomain: string, isPasswordShow: boolean) => {
    if (data.isMongoReplicaSet) {
      return `${getFormatPassword(isPasswordShow)}${entryDomain}/test?replicaSet=${data.cluster_name}&authSource=admin`;
    }
    return `${getFormatPassword(isPasswordShow)}${entryDomain}/test?authSource=admin`;
  };

  const getEntryAccessClb = (data: Props['data'], clusterEntry: ClusterEntryDetailModel[], isPasswordShow: boolean) => {
    if (!data.isMongoReplicaSet) {
      const clbItem = clusterEntry.find((entryItem) => entryItem.cluster_entry_type === 'clbDns');
      if (clbItem) {
        return `${getFormatPassword(isPasswordShow)}${clbItem.entry}:${data.cluster_access_port}/test?authSource=admin`;
      }
    }
    return '';
  };

  const getEntryDomain = (data: Props['data'], clusterEntry: ClusterEntryDetailModel[]) => {
    if (data.isMongoReplicaSet) {
      const domainList = clusterEntry.reduce<string[]>((prevDomainList, entryItem) => {
        if (entryItem.instance_role !== 'backup') {
          return prevDomainList.concat(`${entryItem.entry}:${data.cluster_access_port}`);
        }
        return prevDomainList;
      }, []);
      return domainList.join(',');
    }
    return `${data.master_domain}:${data.cluster_access_port}`;
  };

  const {
    data: clusterEntryData,
    loading: clbLoading,
    run: runGetClusterEntries,
  } = useRequest(getClusterEntries, {
    manual: true,
    onSuccess: (res) => {
      res.forEach((item) => {
        if (item.target_details.length) {
          if (item.isClb) {
            const targetDetailItem = (item as ClusterEntryDetailModel<ClbPolarisTargetDetails>).target_details[0];
            const clbInfo = {
              list: [
                {
                  title: 'IP',
                  value: `${targetDetailItem.clb_ip}:${targetDetailItem.port}`,
                },
                {
                  title: t('CLB域名'),
                  value: `${targetDetailItem.clb_domain}:${targetDetailItem.port}`,
                },
              ],
              title: t('腾讯云负载均衡（CLB）'),
            };
            entryInfo.value = clbInfo;
          }
        }
      });
    },
  });

  const {
    data: passwordData,
    loading: passwordLoading,
    run: runGetPassword,
  } = useRequest(getPassword, {
    manual: true,
  });

  const getDataList = () => {
    const { data } = props;
    const clusterEntryList = clusterEntryData.value || [];

    const entryDomain = getEntryDomain(data, clusterEntryList);
    const entryAccess = getEntryAccess(data, entryDomain, isAccessPasswordShow.value);
    const entryAccessClb = getEntryAccessClb(data, clusterEntryList, isAccessClbPasswordShow.value);

    const infoList: UnwrapRef<typeof dataList> = _.filter(
      [
        {
          label: t('集群名称'),
          type: 'clusterName',
          value: data.cluster_name,
        },
        {
          label: t('域名'),
          type: 'domain',
          value: entryDomain,
        },
        props.data.isShardCluster && {
          label: t('mongos 列表'),
          password: true,
          tag: compareVersions(props.data.major_version.split('-')[1], '4.2') >= 0 ? t('推荐') : '',
          type: 'mongos',
          value: getEntryAccess(
            data,
            data.mongos.map((item) => `${item.ip}:${item.port}`).join(','),
            isMongosPasswordShow.value,
          ),
        },
        {
          label: t('连接字符串'),
          password: true,
          type: 'access',
          value: entryAccess,
        },
      ],
      (item) => !!item,
    );

    if (entryAccessClb) {
      infoList.push({
        label: t('连接字符串（CLB）'),
        password: true,
        type: 'accessClb',
        value: entryAccessClb,
      });
    }

    dataList.value = infoList;
  };

  watch(
    [
      () => props.data,
      clusterEntryData,
      passwordData,
      isMongosPasswordShow,
      isAccessPasswordShow,
      isAccessClbPasswordShow,
    ],
    () => getDataList(),
    { immediate: true },
  );

  watch(
    isShow,
    () => {
      if (isShow.value) {
        runGetClusterEntries({
          bk_biz_id: props.data.bk_biz_id,
          cluster_id: props.data.id,
        });
        runGetPassword({ cluster_id: props.data.id });
      } else {
        entryInfo.value = undefined;
        isMongosPasswordShow.value = false;
        isAccessPasswordShow.value = false;
        isAccessClbPasswordShow.value = false;
      }
    },
    {
      immediate: true,
    },
  );

  const getAccessMap = () => {
    const entryDomain = getEntryDomain(props.data, clusterEntryData.value || []);
    const entryAccess = getEntryAccess(props.data, entryDomain, true);
    const entryAccessClb = getEntryAccessClb(props.data, clusterEntryData.value || [], true);
    const mongosAccess = getEntryAccess(
      props.data,
      props.data.mongos.map((item) => `${item.ip}:${item.port}`).join(','),
      true,
    );

    return {
      access: entryAccess,
      accessClb: entryAccessClb,
      mongos: mongosAccess,
    };
  };

  const handleCopyAll = () => {
    const accessMap = getAccessMap();
    const content = dataList.value.map(
      (dataItem) =>
        `${dataItem.label}：${['access', 'accessClb', 'mongos'].includes(dataItem.type) ? accessMap[dataItem.type as keyof typeof accessMap] : dataItem.value}`,
    );
    if (entryInfo.value) {
      content.push(...entryInfo.value.list.map((valueItem) => `${valueItem.title}：${valueItem.value}`));
    }
    execCopy(content.join('\n'));
  };

  const handleCopy = (value: string, type: string) => {
    const accessMap = getAccessMap();
    execCopy(['access', 'accessClb', 'mongos'].includes(type) ? accessMap[type as keyof typeof accessMap] : value);
  };

  const handlePasswordShow = (type: string) => {
    if (type === 'mongos') {
      isMongosPasswordShow.value = !isMongosPasswordShow.value;
    } else if (type === 'access') {
      isAccessPasswordShow.value = !isAccessPasswordShow.value;
    } else if (type === 'accessClb') {
      isAccessClbPasswordShow.value = !isAccessClbPasswordShow.value;
    }
  };

  const handleClose = () => {
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
  .mongo-access-entry {
    .copy-info {
      position: absolute;
      top: -18px;
      left: 160px;
    }

    .mongo-access-entry-content {
      padding-bottom: 8px;
      font-size: @font-size-mini;
    }

    .mongo-access-entry-item {
      display: flex;
      padding-bottom: 16px;

      .mongo-access-entry-item-label {
        flex-shrink: 0;
        width: 130px;
        text-align: right;
      }

      .mongo-access-entry-item-value {
        color: @title-color;
        word-break: break-all;
      }

      &:hover {
        .copy-btn {
          visibility: visible;
        }
      }

      .copy-btn {
        margin-left: 4px;
        visibility: hidden;
      }
    }

    .cluster-clb-main {
      .main-title {
        margin-bottom: 10px;
        font-size: 12px;
        font-weight: 700;
        color: #313238;
      }

      .item-box {
        display: flex;
        width: 100%;
        height: 28px;
        font-size: 12px;
        align-items: center;

        .item-title {
          width: 118px;
          color: #63656e;
          text-align: right;
        }

        .item-content {
          display: flex;
          overflow: hidden;
          color: #313238;
          flex: 1;
          align-items: center;

          &:hover {
            .copy-btn {
              visibility: visible;
            }
          }

          .icon {
            margin-left: 6px;
            color: #3a84ff;
            cursor: pointer;
          }

          .copy-btn {
            display: inline-block;
            margin-left: 6px;
            font-size: @font-size-mini;
            color: @primary-color;
            cursor: pointer;
            visibility: hidden;
          }
        }
      }
    }
  }
</style>
