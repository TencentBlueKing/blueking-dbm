<!--activeRuleName
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
      style="height: 100%;">
      <div
        class="group-item group-item-all"
        :class="{'active': activeGroup === null}"
        @click.stop="() => handleChangeGroup()">
        <DbIcon
          class="mr-12"
          type="summation" />
        <span
          v-overflow-tips
          class="group-item-name text-overflow">
          {{ t('全部实例') }}
        </span>
        <span class="group-item-nums">{{ totalInstances }}</span>
      </div>
      <span class="split-line" />
      <div class="group-list db-scroll-y">
        <div
          v-for="item in groupList"
          :key="item.id"
          class="group-item"
          :class="{ 'active': activeGroup?.name === item.name}"
          @click.stop="handleChangeGroup(item)">
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
                v-bk-tooltips="t('修改名称')"
                class="group-item-btn mr-8"
                type="edit"
                @click.stop="handleEdit(item.id)" />
              <DbIcon
                v-if="item.instance_count > 0"
                v-bk-tooltips="t('分组下存在实例_不可删除')"
                class="group-item-btn is-disabled"
                type="delete"
                @click.stop />
              <DbPopconfirm
                v-else
                :confirm-handler="() => handleDelete(item)"
                :content="t('删除后将不可恢复_请确认操作')"
                :title="t('确认删除该分组')">
                <DbIcon
                  v-bk-tooltips="t('删除')"
                  class="group-item-btn"
                  type="delete"
                  @click.stop />
              </DbPopconfirm>
            </div>
          </template>
        </div>
      </div>
      <div class="rule-footer">
        <BkButton
          class="rule-add"
          text
          theme="primary"
          @click="handleShowCreateRule">
          <DbIcon type="plus-circle" /> {{ t('新建订阅规则') }}
        </BkButton>
      </div>
    </BkLoading>
  </div>
  <CreateNewRule
    v-model="isShowCreateRule"
    @success="fetchGroupList" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import {
    deleteDumperConfig,
    listDumperConfig,
    updateDumperConfigPartial,
  } from '@services/source/dumper';

  import CreateNewRule from '../create-rule/Index.vue';

  import GroupCreate from './components/Create.vue';

  import { messageSuccess } from '@/utils';

  interface Emits {
    (e: 'change', value: DumperConfig | null): void
  }

  type DumperConfig = ServiceReturnType<typeof listDumperConfig>['results'][number]

  const emits = defineEmits<Emits>();

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const activeGroup = ref<DumperConfig | null>(null);
  const isLoading = ref(false);
  const groupList = ref<Array<DumperConfig>>([]);
  const curEditGroupId = ref(0);
  const isShowCreateRule = ref(false);


  const totalInstances = computed(() => (
    groupList.value.reduce((total: number, item) => total + (item.instance_count ?? 0), 0)
  ));

  const dumperId = Number(route.params.dumperId);

  const fetchGroupList = () => {
    isLoading.value = true;
    listDumperConfig({
      offset: 0,
      limit: -1,
    })
      .then((data) => {
        groupList.value = data.results;
        if (dumperId) {
          const item = data.results.find(item => item.id === dumperId);
          handleChangeGroup(item);
        }
      })
      .catch(() => {
        groupList.value = [];
      })
      .finally(() => {
        isLoading.value = false;
      });
  };
  fetchGroupList();

  const handleChangeGroup = (item?: DumperConfig) => {
    router.replace({
      params: { dumperId: item?.id ?? 0 },
    });
    emits('change', item ?? null);
    if (item) {
      activeGroup.value = item;
      return;
    }
    activeGroup.value = null;
  };

  const handleCloseEdit = () => {
    curEditGroupId.value = 0;
  };

  const handleUpdateName = (item: DumperConfig, name: string) => {
    const { id } = item;
    updateDumperConfigPartial({
      id,
      name,
    }).then((res) => {
      if (res.name) {
        Object.assign(item, { name });
      }
      curEditGroupId.value = 0;
    });
  };

  const handleEdit = (id: number) => {
    curEditGroupId.value = id;
  };


  const handleDelete = (item: DumperConfig) => {
    if (item.instance_count === 0) {
      deleteDumperConfig({ id: item.id })
        .then((result) => {
          if (!result) {
            messageSuccess(t('删除成功'));
            fetchGroupList();
          }
        });
    }
  };

  const handleShowCreateRule = () => {
    isShowCreateRule.value = true;
  };

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

  .group-item-all {
    padding-right: 20px;
  }

  .rule-footer {
    display: flex;
    align-items: center;
    height: 36px;
    padding: 0 16px;
    font-size: 12px;
    line-height: 36px;
  }

  .rule-add {
    color: #3A84FF;

    .db-icon-plus-circle {
      margin-right: 4px;
      font-size: 14px;
    }
  }
}
</style>
