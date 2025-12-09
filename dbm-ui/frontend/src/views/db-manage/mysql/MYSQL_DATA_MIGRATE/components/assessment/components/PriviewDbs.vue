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
  <BkSideslider
    v-model:is-show="isShow"
    :width="900"
    @close="handleClose">
    <template #header>
      <span>{{ t('最终DB') }}</span>
      <BkTag class="ml-10">{{ t('源集群：') }}{{ data.source }}</BkTag>
    </template>
    <div class="merge-disk-space-priview-dbs">
      <BkTable
        border
        :data="tableData">
        <BkTableColumn
          field="clone_db_list"
          :label="t('克隆 DB 名')"
          :min-width="200">
          <template #default="{ row }: { row: MysqlMergeDiskSpaceModel }">
            <BkTag
              v-for="dbname in row.clone_db_list"
              :key="dbname">
              {{ dbname }}
            </BkTag>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="ignore_db_list"
          :label="t('忽略 DB')"
          :min-width="200">
          <template #default="{ row }: { row: MysqlMergeDiskSpaceModel }">
            <BkTag
              v-for="dbname in row.ignore_db_list"
              :key="dbname">
              {{ dbname }}
            </BkTag>
          </template>
        </BkTableColumn>
      </BkTable>
      <div class="mt-24 mb-12">
        <span class="db-list-title">{{ t('DB 列表') }}</span>
        <span class="ml-6">
          {{ t('( 共 x 个，共 y G )', { x: dbList.length, y: dbList.reduce((acc, cur) => acc + cur.size, 0) }) }}
        </span>
      </div>
      <BkTable
        border
        :data="dbList">
        <BkTableColumn
          field="name"
          :label="t('DB 名称')"
          :min-width="200" />
        <BkTableColumn
          field="size"
          :label="t('DB 大小 ( G )')"
          :min-width="200">
          <template #default="{ row }: { row: { name: string; size: number } }">
            {{ row.size || '--' }}
          </template>
        </BkTableColumn>
      </BkTable>
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type MysqlMergeDiskSpaceModel from '@services/model/mysql/mysql-merge-disk-space';

  interface Props {
    data: MysqlMergeDiskSpaceModel;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();

  const tableData = shallowRef<MysqlMergeDiskSpaceModel[]>([]);
  const dbList = shallowRef<
    {
      name: string;
      size: number;
    }[]
  >([]);

  watch(
    isShow,
    () => {
      if (isShow.value) {
        tableData.value = [props.data];
        dbList.value = props.data.db_list.map((item) => ({
          name: item,
          size: props.data.db_size[item],
        }));
      }
    },
    {
      immediate: true,
    },
  );

  const handleClose = () => {
    isShow.value = false;
    tableData.value = [];
    dbList.value = [];
  };
</script>
<style lang="less" scoped>
  .merge-disk-space-priview-dbs {
    margin: 18px 24px;

    .db-list-title {
      font-family: MicrosoftYaHei-Bold;
      font-weight: 700;
      font-size: 14px;
      color: #313238;
      letter-spacing: 0;
      line-height: 22px;
    }
  }
</style>
