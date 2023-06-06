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
  <div class="apply">
    <div class="apply-services db-scroll-y">
      <DbCard :title="$t('全部服务')">
        <ApplyCollapse
          v-for="item of services"
          :key="item.name"
          class="apply-collapse">
          <template #title>
            <img
              :src="getIconPath(item.iconName)"
              width="28">
            <strong class="apply-collapse__name">{{ item.name }}</strong>
            <BkTag class="apply-collapse__count">
              {{ item.children.length }}
            </BkTag>
          </template>
          <div class="apply-collapse__content">
            <div
              v-for="child of item.children"
              :key="child.id"
              class="apply-item"
              @click="handleApply(child)">
              <BkPopover
                :disabled="!child.tipImgProps"
                placement="bottom"
                theme="light">
                <div class="apply-item__trigger">
                  <i
                    class="apply-item__icon"
                    :class="[child.icon]" />
                  <span
                    v-overflow-tips
                    class="apply-item__name text-overflow">{{ child.name }}</span>
                </div>
                <template #content>
                  <div class="apply-collapse__content__popover">
                    <img v-bind="child.tipImgProps">
                  </div>
                </template>
              </BkPopover>
            </div>
          </div>
        </ApplyCollapse>
      </DbCard>
    </div>
    <Copyright />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useMainViewStore } from '@stores';

  import {
    bigDataType,
    ClusterTypes,
    mysqlType,
    redisType,
    TicketTypes,
  } from '@common/const';

  import Copyright from '@components/layouts/Copyright.vue';

  import ApplyCollapse from './components/ApplyCollapse.vue';

  import haTipImg from '@/images/architecture-01.png';
  import singleTipImg from '@/images/architecture-02.png';

  interface IService {
    iconName: string,
    name: string,
    children: Array<{
      id: TicketTypes,
      routeName: string,
      name: string,
      icon: string,
      type: ClusterTypes,
      tipImgProps?: {
        width: number,
        src: string,
      },
    }>
  }

  const router = useRouter();
  const { t } = useI18n();

  const mainViewStore = useMainViewStore();
  mainViewStore.hasPadding = false;

  // 全部服务类型
  const services: Array<IService> = [
    {
      iconName: 'mysql',
      name: 'MySQL',
      children: [
        {
          routeName: 'SelfServiceApplySingle',
          id: mysqlType[TicketTypes.MYSQL_SINGLE_APPLY].id,
          name: mysqlType[TicketTypes.MYSQL_SINGLE_APPLY].name,
          type: mysqlType[TicketTypes.MYSQL_SINGLE_APPLY].type,
          icon: 'db-icon-mysql',
          tipImgProps: {
            width: 150,
            src: singleTipImg,
          },
        },
        {
          routeName: 'SelfServiceApplyHa',
          id: mysqlType[TicketTypes.MYSQL_HA_APPLY].id,
          name: mysqlType[TicketTypes.MYSQL_HA_APPLY].name,
          type: mysqlType[TicketTypes.MYSQL_HA_APPLY].type,
          icon: 'db-icon-mysql',
          tipImgProps: {
            width: 362,
            src: haTipImg,
          },
        },
      ],
    },
    {
      iconName: 'redis',
      name: 'Redis',
      children: [
        {
          routeName: 'SelfServiceApplyRedis',
          id: redisType[TicketTypes.REDIS_CLUSTER_APPLY].id,
          name: redisType[TicketTypes.REDIS_CLUSTER_APPLY].name,
          type: redisType[TicketTypes.REDIS_CLUSTER_APPLY].type,
          icon: 'db-icon-redis',
        },
      ],
    },
    {
      iconName: 'mongo-db',
      name: t('大数据'),
      children: [
        {
          routeName: 'EsApply',
          id: bigDataType[TicketTypes.ES_APPLY].id,
          name: bigDataType[TicketTypes.ES_APPLY].name,
          icon: 'db-icon-es',
          type: bigDataType[TicketTypes.ES_APPLY].type,
        },
        {
          routeName: 'KafkaApply',
          id: bigDataType[TicketTypes.KAFKA_APPLY].id,
          name: bigDataType[TicketTypes.KAFKA_APPLY].name,
          icon: 'db-icon-kafka',
          type: bigDataType[TicketTypes.KAFKA_APPLY].type,
        },
        {
          routeName: 'HdfsApply',
          id: bigDataType[TicketTypes.HDFS_APPLY].id,
          name: bigDataType[TicketTypes.HDFS_APPLY].name,
          icon: 'db-icon-hdfs',
          type: bigDataType[TicketTypes.HDFS_APPLY].type,
        },
        {
          routeName: 'PulsarApply',
          id: bigDataType[TicketTypes.PULSAR_APPLY].id,
          name: bigDataType[TicketTypes.PULSAR_APPLY].name,
          icon: 'db-icon-pulsar',
          type: bigDataType[TicketTypes.PULSAR_APPLY].type,
        },
        {
          routeName: 'SelfServiceApplyInfluxDB',
          id: bigDataType[TicketTypes.INFLUXDB_APPLY].id,
          name: bigDataType[TicketTypes.INFLUXDB_APPLY].name,
          icon: 'db-icon-influxdb',
          type: bigDataType[TicketTypes.INFLUXDB_APPLY].type,
        },
        {
          routeName: 'SelfServiceApplyTenDB',
          id: bigDataType[TicketTypes.TENDB_APPLY].id,
          name: bigDataType[TicketTypes.TENDB_APPLY].name,
          icon: 'db-icon-influxdb',
          type: bigDataType[TicketTypes.TENDB_APPLY].type,
        },
      ],
    },
  ];

  function getIconPath(name: string) {
    return new URL(`../../images/${name}.png`, import.meta.url).href;
  }

  function handleApply(item: IService['children'][0]) {
    router.push({
      name: item.routeName,
    });
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .apply {
    display: flex;
    height: 100%;
    flex-direction: column;
    padding: 24px 24px 0;

    &-services {
      flex: 1;
    }
  }

  .apply-collapse {
    margin-bottom: 16px;
    line-height: 28px;

    &:last-child {
      margin-bottom: 0;
    }

    &__name {
      margin: 0 8px 0 12px;
      color: @title-color;
    }

    &__count {
      height: 16px;
      line-height: 16px;
      color: @gray-color;
    }

    &__content {
      display: grid;
      grid-template-columns: repeat(6, 1fr);
      grid-column-gap: 16px;
    }
  }

  .apply-item {
    width: 100%;
    padding: 0 8px 0 16px;
    margin: 4px 16px 4px 0;
    font-size: @font-size-mini;
    line-height: 40px;
    cursor: pointer;
    background-color: @bg-gray;
    border-radius: 2px;

    &__name {
      flex: 1;
    }

    &__icon {
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

      .apply-item__icon {
        background-color: @bg-disable;
      }
    }

    &__trigger {
      .flex-center();
    }
  }

  @media screen and (max-width: 1366px) {
    .apply-collapse__content {
      grid-template-columns: repeat(3, 1fr);
    }
  }

  @media screen and (min-width: 1366px) and (max-width: 1680px) {
    .apply-collapse__content {
      grid-template-columns: repeat(4, 1fr);
    }
  }

  @media screen and (min-width: 1680px) and (max-width: 1920px) {
    .apply-collapse__content {
      grid-template-columns: repeat(5, 1fr);
    }
  }
</style>
