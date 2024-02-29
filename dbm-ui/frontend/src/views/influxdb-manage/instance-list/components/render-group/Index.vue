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
  <div class="group-wrapper">
    <BkLoading
      :loading="isLoading"
      style="height: 100%">
      <div
        class="group-item group-item--all"
        :class="{ active: activeGroupId === 0 }"
        @click.stop="handleChangeGroup(0)">
        <DbIcon
          class="mr-12"
          type="summation" />
        <span
          v-overflow-tips
          class="group-item-name text-overflow">
          {{ $t('全部实例') }}
        </span>
        <span class="group-item-nums">{{ totalInstances }}</span>
      </div>
      <span class="split-line" />
      <div class="group-list db-scroll-y">
        <div
          v-for="item in groupList"
          :key="item.id"
          class="group-item"
          :class="{ active: activeGroupId === item.id }"
          @click.stop="handleChangeGroup(item.id)">
          <template v-if="curEditGroupId === item.id">
            <GroupCreate
              :origin-name="item.name"
              @change="(name) => handleUpdateName(item, name)"
              @close="handleCloseEdit" />
          </template>
          <template v-else>
            <DbIcon
              class="mr-12"
              type="folder-open" />
            <span
              v-overflow-tips
              class="group-item-name text-overflow">
              {{ item.name }}
            </span>
            <span class="group-item-nums">{{ item.instance_count }}</span>
            <div class="group-item-operations">
              <DbIcon
                v-bk-tooltips="$t('修改名称')"
                class="group-item-btn mr-8"
                type="edit"
                @click.stop="handleEdit(item.id)" />
              <DbIcon
                v-if="item.instance_count > 0"
                v-bk-tooltips="$t('分组下存在实例_不可删除')"
                class="group-item-btn is-disabled"
                type="delete"
                @click.stop />
              <DbPopconfirm
                v-else
                :confirm-handler="() => handleDelete(item)"
                :content="$t('删除后将不可恢复_请确认操作')"
                :title="$t('确认删除该分组')">
                <DbIcon
                  v-bk-tooltips="$t('删除')"
                  class="group-item-btn"
                  type="delete"
                  @click.stop />
              </DbPopconfirm>
            </div>
          </template>
        </div>
      </div>
      <div class="group-footer">
        <GroupCreate
          v-if="isShowCreateGroup"
          @change="handleCreateGroup"
          @close="handleCreateClose" />
        <a
          v-else
          class="group-add"
          href="javascript:"
          @click="handleShowCreateGroup">
          <DbIcon type="plus-circle" />
          {{ $t('添加分组') }}
        </a>
      </div>
    </BkLoading>
  </div>
</template>

<script setup lang="ts">
  import type { Emitter } from 'mitt';
  import { useI18n } from 'vue-i18n';

  import { createGroup, deleteGroup, getGroupList, updateGroupInfo } from '@services/source/influxdbGroup';
  import type { InfluxDBGroupItem } from '@services/types/influxdbGroup';

  import GroupCreate from './components/Create.vue';

  import { useGlobalBizs } from '@/stores';
  import { messageSuccess } from '@/utils';

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const eventBus = inject('eventBus') as Emitter<Record<any, unknown>>;

  const activeGroupId = ref(0);
  const isLoading = ref(false);
  const groupList = ref<Array<InfluxDBGroupItem>>([]);
  const curEditGroupId = ref(0);
  const isShowCreateGroup = ref(false);
  const totalInstances = computed(() =>
    groupList.value.reduce((total: number, item) => total + (item.instance_count ?? 0), 0),
  );

  watch(
    () => groupList,
    () => {
      eventBus.emit('update-group-list', groupList.value);
    },
    { immediate: true, deep: true },
  );

  const hasGroupId = (id: number) => !!groupList.value.find((item) => item.id === id) || id === 0;
  const setGroupId = (id: number) => {
    let groupId = id;
    if (groupId === activeGroupId.value) {
      return;
    }

    if (hasGroupId(groupId) === false) {
      groupId = 0;
    }

    activeGroupId.value = groupId;
    router.replace({
      params: { groupId },
    });
  };

  const fetchGroupList = () => {
    isLoading.value = true;
    getGroupList({ bk_biz_id: currentBizId })
      .then((data) => {
        groupList.value = data.results;
        setGroupId(Number(route.params.groupId));
      })
      .catch(() => {
        groupList.value = [];
      })
      .finally(() => {
        isLoading.value = false;
      });
  };
  fetchGroupList();

  const handleChangeGroup = (id: number) => {
    setGroupId(id);
  };

  const handleEdit = (id: number) => {
    curEditGroupId.value = id;
  };

  const handleCloseEdit = () => {
    curEditGroupId.value = 0;
  };

  const handleDelete = (item: InfluxDBGroupItem) => {
    if (item.instance_count === 0) {
      deleteGroup({ id: item.id }).then(() => {
        messageSuccess(t('删除成功'));
        fetchGroupList();
        handleChangeGroup(0);
      });
    }
  };

  const handleUpdateName = (item: InfluxDBGroupItem, name: string) => {
    // 失焦的同时点击了另外一个分组的编辑则默认不保存上次编辑内容
    setTimeout(() => {
      const { id } = item;
      if (id === curEditGroupId.value) {
        updateGroupInfo({
          id,
          bk_biz_id: item.bk_biz_id,
          name,
        }).then(() => {
          Object.assign(item, { name });
          curEditGroupId.value = 0;
        });
      }
    });
  };

  const handleShowCreateGroup = () => {
    isShowCreateGroup.value = true;
  };

  const handleCreateGroup = (name: string) => {
    createGroup({
      bk_biz_id: currentBizId,
      name,
    }).then((res) => {
      messageSuccess(t('创建成功'));
      groupList.value.push(res);
    });
  };

  const handleCreateClose = () => {
    isShowCreateGroup.value = false;
  };

  eventBus.on('fetch-group-list', fetchGroupList);
  onBeforeUnmount(() => {
    eventBus.off('fetch-group-list', fetchGroupList);
  });
</script>

<style lang="less" scoped>
  .group-wrapper {
    height: 100%;
    padding-top: 16px;

    .split-line {
      display: block;
      height: 1px;
      margin: 8px 0;
      background-color: #dcdee5;
    }

    .group-list {
      max-height: calc(100% - 86px);
    }

    .group-item {
      display: flex;
      height: 36px;
      padding: 0 16px;
      font-size: 12px;
      line-height: 36px;
      cursor: pointer;
      align-items: center;

      .group-item-name {
        flex: 1;
      }

      .group-item-nums {
        padding: 0 6px;
        line-height: 16px;
        color: @gray-color;
        background-color: #eaebf0;
        border-radius: 2px;
      }

      .group-item-operations {
        display: none;
      }

      .group-item-btn {
        &.is-disabled {
          color: @light-gray;
          cursor: not-allowed;
        }
      }

      &:hover {
        background-color: #eaebf0;

        &:not(.group-item--all) {
          .group-item-operations {
            display: block;
          }

          .group-item-nums {
            display: none;
          }
        }
      }

      &.active {
        color: @primary-color;
        background-color: #e1ecff;

        .group-item-nums {
          color: white;
          background-color: #a3c5fd;
        }
      }
    }

    .group-footer {
      display: flex;
      align-items: center;
      height: 36px;
      padding: 0 16px;
      font-size: 12px;
      line-height: 36px;
    }

    .group-add {
      .db-icon-plus-circle {
        margin-right: 4px;
        font-size: 14px;
      }
    }
  }
</style>
