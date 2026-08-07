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
    class="service-apply-page"
    style="height: calc(100vh - var(--notice-height) - 124px)">
    <ScrollFaker style="height: calc(100% - 72px)">
      <ApplyCollapse
        v-if="historyCacheIdDisplayList.length > 0"
        class="apply-collapse">
        <template #title>
          {{ t('最近使用') }}
        </template>
        <div class="history-list">
          <div
            v-for="id in historyCacheIdDisplayList"
            :key="id"
            class="history-item"
            @click="handleApply(serviceIdMap[id])">
            <DbIcon
              class="item-icon"
              :type="serviceIdMap[id]?.icon" />
            <div class="item-text">
              {{ serviceIdMap[id]?.name }}
            </div>
            <div style="padding: 20px 0 20px 8px; margin-left: auto">
              <DbIcon
                v-if="favorIdMap[id]"
                style="color: #ffb848"
                type="star-fill"
                @click.stop="handleUnfavor(id)" />
              <DbIcon
                v-else
                class="favor-btn"
                type="star"
                @click.stop="handleFavor(id)" />
            </div>
          </div>
        </div>
      </ApplyCollapse>
      <FunController
        v-for="item of displayServices"
        :key="item.name"
        :module-id="item.id">
        <ApplyCollapse
          v-if="item.children.length > 0"
          class="apply-collapse">
          <template #title>
            {{ item.name }}
            <BkTag class="apply-collapse-count">
              {{ item.children.length }}
            </BkTag>
          </template>
          <div class="apply-collapse-content">
            <div
              v-if="item.groupName"
              class="group-name">
              {{ item.groupName }}
            </div>
            <div
              v-for="child of item.children"
              :key="child.id"
              class="apply-item"
              @click="handleApply(child)">
              <BkPopover
                :disabled="!child.tipImgProps"
                placement="bottom"
                theme="light">
                <div class="apply-item-wrapper">
                  <DbIcon
                    class="apply-item-icon"
                    :type="child.icon" />
                  <span>
                    {{ child.name }}
                  </span>
                </div>
                <template #content>
                  <img v-bind="child.tipImgProps" />
                </template>
              </BkPopover>
            </div>
          </div>
        </ApplyCollapse>
      </FunController>
    </ScrollFaker>
    <Copyright />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type {
    ExtractedControllerDataKeys,
    FunctionKeys,
  } from '@services/model/function-controller/functionController';

  import { useFunController, useUserProfile } from '@stores';

  import { TicketTypes, UserPersonalSettings } from '@common/const';

  import { makeMap } from '@utils';

  import haTipImg from '@images/architecture-01.png';
  import singleTipImg from '@images/architecture-02.png';

  import ApplyCollapse from './components/ApplyCollapse.vue';
  import Copyright from './components/Copyright.vue';

  interface IService {
    children: Array<{
      controllerId?: FunctionKeys;
      icon: string;
      id: TicketTypes;
      name: string;
      tipImgProps?: {
        src: string;
        width: number;
      };
    }>;
    groupName?: string;
    id: ExtractedControllerDataKeys;
    name: string;
  }

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const userProfile = useUserProfile();
  const funControllerStore = useFunController();

  const localHistroyKey = 'SERVICE_APPLY_HISTORY';

  // 全部服务类型
  const services: Array<IService> = [
    {
      children: [
        {
          controllerId: 'tendbsingle',
          icon: 'mysql',
          id: TicketTypes.MYSQL_SINGLE_APPLY,
          name: t('单节点部署'),
          tipImgProps: {
            src: singleTipImg,
            width: 150,
          },
        },
        {
          controllerId: 'tendbha',
          icon: 'mysql',
          id: TicketTypes.MYSQL_HA_APPLY,
          name: t('主从部署'),
          tipImgProps: {
            src: haTipImg,
            width: 362,
          },
        },
        {
          controllerId: 'tendbcluster',
          icon: 'mysql',
          id: TicketTypes.TENDBCLUSTER_APPLY,
          name: t('TendbCluster分布式集群部署'),
        },
      ],
      groupName: 'MySQL',
      id: 'mysql',
      name: '关系型数据库',
    },
    {
      children: [
        {
          controllerId: 'sqlserver_single',
          icon: 'sqlserver',
          id: TicketTypes.SQLSERVER_SINGLE_APPLY,
          name: t('单节点部署'),
        },
        {
          controllerId: 'sqlserver_ha',
          icon: 'sqlserver',
          id: TicketTypes.SQLSERVER_HA_APPLY,
          name: t('主从部署'),
        },
      ],
      groupName: 'SQLServer',
      id: 'sqlserver',
      name: '关系型数据库',
    },
    {
      children: [
        {
          icon: 'redis',
          id: TicketTypes.REDIS_CLUSTER_APPLY,
          name: t('Redis集群部署'),
        },
        {
          icon: 'redis',
          id: TicketTypes.REDIS_INS_APPLY,
          name: t('主从部署'),
        },
      ],
      groupName: 'Redis',
      id: 'redis',
      name: 'NoSQL数据库',
    },
    {
      children: [
        {
          icon: 'mongo-db',
          id: TicketTypes.MONGODB_SHARD_APPLY,
          name: t('MongoDB分片集群部署'),
        },
        {
          icon: 'mongo-db',
          id: TicketTypes.MONGODB_REPLICASET_APPLY,
          name: t('MongoDB副本集部署'),
        },
      ],
      groupName: 'Mongodb',
      id: 'mongodb',
      name: 'NoSQL数据库',
    },
    {
      children: [
        {
          controllerId: 'influxdb',
          icon: 'influxdb',
          id: TicketTypes.INFLUXDB_APPLY,
          name: t('InfluxDB集群部署'),
        },
      ],
      id: 'bigdata',
      name: '时序数据库',
    },
    {
      children: [
        {
          controllerId: 'es',
          icon: 'es',
          id: TicketTypes.ES_APPLY,
          name: t('ES集群部署'),
        },
        {
          controllerId: 'hdfs',
          icon: 'hdfs',
          id: TicketTypes.HDFS_APPLY,
          name: t('HDFS集群部署'),
        },
        {
          controllerId: 'doris',
          icon: 'doris',
          id: TicketTypes.DORIS_APPLY,
          name: t('Doris集群部署'),
        },
      ],
      id: 'bigdata',
      name: t('大数据'),
    },
    {
      children: [
        {
          controllerId: 'pulsar',
          icon: 'pulsar',
          id: TicketTypes.PULSAR_APPLY,
          name: t('Pulsar集群部署'),
        },
        {
          controllerId: 'kafka',
          icon: 'kafka',
          id: TicketTypes.KAFKA_APPLY,
          name: t('Kafka集群部署'),
        },
        {
          controllerId: 'riak',
          icon: 'cluster',
          id: TicketTypes.RIAK_CLUSTER_APPLY,
          name: t('Riak集群部署'),
        },
      ],
      id: 'bigdata',
      name: '消息队列',
    },
  ];

  const serviceIdMap = Object.values(services).reduce<
    Record<string, { moduleId: IService['id'] } & IService['children'][number]>
  >((result, groupItem) => {
    groupItem.children.forEach((item) => {
      Object.assign(result, {
        [item.id]: { ...item, moduleId: groupItem.id },
      });
    });
    return result;
  }, {});

  const lastFavorIdMap = makeMap(userProfile.profile[UserPersonalSettings.SERVICE_APPLY_FAVOR] || []);

  const displayServices = services.map((serviceItem) => {
    const displayChildren = serviceItem.children.filter((childItem) => {
      const { controllerId } = childItem;
      const { id: moduleId } = serviceItem;
      const funControllerData = funControllerStore.funControllerData.getFlatData(moduleId);

      if (controllerId) {
        return funControllerData[controllerId];
      }
      return funControllerData[moduleId];
    }, []);
    return { ...serviceItem, children: displayChildren };
  });

  const historyCacheIdList = ref<string[]>(
    _.sortBy(JSON.parse(localStorage.getItem(localHistroyKey) || '[]'), (item) => lastFavorIdMap[item]),
  );
  const favorIdMap = shallowRef({ ...lastFavorIdMap });

  const historyCacheIdDisplayList = computed(() =>
    historyCacheIdList.value.filter((cacheItem) => {
      const childItem = serviceIdMap[cacheItem];
      const { controllerId, moduleId } = childItem;
      const funControllerData = funControllerStore.funControllerData.getFlatData(moduleId);

      if (controllerId) {
        return funControllerData[controllerId];
      }
      return funControllerData[moduleId];
    }),
  );

  const handleApply = (item: IService['children'][number]) => {
    localStorage.setItem(localHistroyKey, JSON.stringify(_.uniq([item.id, ...historyCacheIdList.value]).slice(0, 6)));

    router.push({
      name: item.id,
      query: {
        bizId: route.name === 'BussinessServiceApplyIndex' ? window.PROJECT_CONFIG.BIZ_ID : undefined,
        from: route.name as string,
      },
    });
  };

  const handleUnfavor = (id: string) => {
    const lastFavorIdMap = { ...favorIdMap.value };
    delete lastFavorIdMap[id];
    favorIdMap.value = lastFavorIdMap;
    userProfile.updateProfile({
      label: UserPersonalSettings.SERVICE_APPLY_FAVOR,
      values: Object.keys(lastFavorIdMap),
    });
  };
  const handleFavor = (id: string) => {
    const lastFavorIdMap = {
      ...favorIdMap.value,
      [id]: true,
    };
    favorIdMap.value = lastFavorIdMap;
    userProfile.updateProfile({
      label: UserPersonalSettings.SERVICE_APPLY_FAVOR,
      values: Object.keys(lastFavorIdMap),
    });
  };
</script>
<style lang="less">
  @import '@styles/mixins.less';

  .service-apply-page {
    .history-list {
      display: flex;

      .history-item {
        display: flex;
        width: 250px;
        height: 56px;
        padding: 0 16px;
        margin-right: 16px;
        overflow: hidden;
        font-size: 12px;
        color: #63656e;
        cursor: pointer;
        background: #f5f7fa;
        border-radius: 2px;
        transition: all 0.1s;
        align-items: center;

        &:hover {
          background: #f0f1f5;

          .favor-btn {
            opacity: 100%;
          }
        }

        .item-icon {
          display: flex;
          flex: 0 0 32px;
          width: 32px;
          height: 32px;
          margin-right: 8px;
          background: #eaebf0;
          border-radius: 50%;
          align-items: center;
          justify-content: center;
        }

        .item-text {
          height: 16px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .favor-btn {
          opacity: 0%;
          transition: all 0.1s;
        }
      }
    }

    .apply-collapse {
      margin-bottom: 16px;

      &:last-child {
        margin-bottom: 0;
      }

      .apply-collapse-count {
        height: 16px;
        margin-left: 4px;
        line-height: 16px;
        color: @gray-color;
      }
    }

    .apply-collapse-content {
      display: flex;

      .group-name {
        display: flex;
        width: 100px;
        height: 40px;
        margin-right: 16px;
        font-size: 12px;
        font-weight: bold;
        color: #313238;
        background: #eaebf0;
        border-radius: 2px;
        align-items: center;
        justify-content: center;
      }
    }

    .apply-item {
      width: 290px;
      padding: 0 16px;
      margin-right: 16px;
      font-size: @font-size-mini;
      line-height: 40px;
      cursor: pointer;
      background-color: #f5f7fa;
      border-radius: 2px;

      .apply-item-wrapper {
        display: flex;
        height: 40px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 0 0 auto;
        align-items: center;
      }

      .apply-item-icon {
        width: 24px;
        height: 24px;
        margin-right: 8px;
        font-size: @font-size-large;
        line-height: 24px;
        background-color: #eaebf0;
        border-radius: 50%;
        flex-shrink: 0;
      }

      &:hover {
        background-color: @bg-dark-gray;

        .apply-item-icon {
          background-color: @bg-disable;
        }
      }
    }
  }
</style>
