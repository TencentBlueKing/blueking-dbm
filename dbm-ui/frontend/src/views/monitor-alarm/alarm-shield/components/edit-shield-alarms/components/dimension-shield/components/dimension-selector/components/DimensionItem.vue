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
  <div class="dimension-item-main">
    <div class="left-box">
      <div
        v-if="!isSingle && showLink"
        class="item-box other">
        <div class="item">
          <span class="top-bar" />
          AND
          <span class="bottom-bar" />
        </div>
      </div>
    </div>
    <div class="right-box">
      <div class="item-box">
        <span
          v-if="!isSingle"
          class="left-bar" />
        <div class="title-box">
          <BkSelect
            v-model="titleValue"
            class="title-select"
            :clearable="false"
            :disabled="isFixed || disabled"
            :filterable="false"
            @change="handleTypeChange">
            <BkOption
              v-for="item in titleList"
              :key="item.value"
              :label="item.label"
              :value="item.value" />
          </BkSelect>
        </div>
        <BkDropdown :disabled="isFixed || disabled">
          <div
            class="operaion-sign"
            :class="{ 'operaion-sign-disabled': isFixed }">
            {{ operationSign.label }}
          </div>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem
                v-for="(item, index) in operationList"
                :key="index"
                @click="() => handleChooseSignClick(item)">
                {{ item.label }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
        <div class="content">
          <BkSelect
            v-model="contentValue"
            allow-create
            collapse-tags
            :disabled="isFixed || disabled"
            filterable
            multiple
            multiple-mode="tag"
            @change="handleContentChange">
            <BkOption
              v-for="item in selectList"
              :key="item.value"
              :label="item.label"
              :value="item.value" />
          </BkSelect>
        </div>
        <div class="operate-box">
          <i
            v-if="showAdd"
            class="db-icon-plus-fill icon plus"
            :class="{ 'no-active-icon': disabled || !enableAdd }"
            @click="handleLClickAdd" />
          <i
            v-if="showDelete"
            class="db-icon-minus-fill icon minus"
            :class="{ 'no-active-icon': disabled || !enableDelete }"
            @click="handleClickDelete" />
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import AlarmShieldModel from '@services/model/monitor/alarm-shield';
  import { getClusterList, getInstanceList, getIpList, getRoleList } from '@services/source/monitor';

  import { useGlobalBizs } from '@stores';

  import { batchInputSplitRegex } from '@common/regex';

  interface Props {
    data?: AlarmShieldModel['dimension_config']['dimension_conditions'][number];
    dbType?: string;
    disabled?: boolean;
    enableAdd?: boolean;
    enableDelete?: boolean;
    excludes?: string[];
    isFixed?: boolean;
    isSingle?: boolean;
    showAdd?: boolean;
    showDelete?: boolean;
    showLink?: boolean;
  }

  interface Emits {
    (e: 'add'): void;
    (e: 'delete'): void;
    (e: 'typeChange', value: string): void;
  }

  interface Exposes {
    getValue: () => {
      key: string;
      method: string;
      values: (string | number)[];
    };
  }

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    dbType: '',
    disabled: false,
    enableAdd: true,
    enableDelete: true,
    excludes: () => [],
    isFixed: false,
    isSingle: false,
    showAdd: true,
    showDelete: true,
    showLink: false,
  });

  const emits = defineEmits<Emits>();

  const fetchInstanceList = (params: ServiceParameters<typeof getInstanceList>) =>
    getInstanceList(params).then((data) =>
      data.map((item) => {
        const [ip, port] = item.split('-');
        return `${ip}:${port}`;
      }),
    );

  const { t } = useI18n();
  const { currentBizInfo } = useGlobalBizs();

  const handleTypeChange = (value: string, isReset = true) => {
    if (isReset) {
      contentValue.value = [];
      selectList.value = [];
      return;
    }

    const requestHandler = serviceMap[value as keyof typeof serviceMap];
    const params: {
      bk_biz_id: number;
      dbtype?: string;
    } = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      dbtype: props.dbType,
    };
    if (!props.dbType) {
      delete params.dbtype;
    }
    requestHandler(params).then((data) => {
      selectList.value = data.map((item) => ({
        label: item,
        value: item,
      }));
    });
    setTimeout(() => {
      emits('typeChange', value);
    });
  };

  const titleTotalList = [
    {
      label: t('业务'),
      value: 'appid',
    },
    {
      label: t('集群'),
      value: 'cluster_domain',
    },
    {
      label: t('角色'),
      value: 'instance_role',
    },
    {
      label: t('实例'),
      value: 'instance',
    },
    {
      label: 'IP',
      value: 'instance_host',
    },
  ];

  const serviceMap = {
    cluster_domain: getClusterList,
    instance: fetchInstanceList,
    instance_host: getIpList,
    instance_role: getRoleList,
  };

  const titleValue = ref('');
  const contentValue = ref<(string | number)[]>([]);
  const operationSign = ref({
    label: '=',
    value: 'eq',
  });
  const selectList = ref<
    {
      label: string;
      value: string | number;
    }[]
  >([]);

  const titleList = computed(() => {
    if (props.excludes.length === 1 && props.isSingle) {
      return titleTotalList;
    }

    return titleTotalList.filter((item) => !props.excludes.includes(item.value));
  });

  const operationList = [
    {
      label: '=',
      value: 'eq',
    },
    {
      label: '!=',
      value: 'neq',
    },
    {
      label: 'include',
      value: 'include',
    },
    {
      label: 'exclude',
      value: 'exclude',
    },
    {
      label: 'regex',
      value: 'regex',
    },
    {
      label: 'nregex',
      value: 'nregex',
    },
  ];

  watchEffect(() => {
    if (props.isFixed) {
      titleValue.value = 'appid';
    }
  });

  watchEffect(() => {
    if (props.data?.name) {
      titleValue.value = props.data.name;
      contentValue.value = props.data.value;
      operationSign.value = {
        label: operationList.find((item) => item.value === props.data!.method)!.label,
        value: props.data.method,
      };
    }
  });

  watch(
    titleValue,
    () => {
      if (titleValue.value) {
        if (titleValue.value === 'appid') {
          contentValue.value = [currentBizInfo!.bk_biz_id];
          selectList.value = [
            {
              label: currentBizInfo!.name,
              value: currentBizInfo!.bk_biz_id,
            },
          ];
          return;
        }

        handleTypeChange(titleValue.value, false);
      }
    },
    {
      immediate: true,
    },
  );

  const handleContentChange = (list: string[]) => {
    const hadnledList = list.map((item) => item.split(batchInputSplitRegex));
    contentValue.value = _.flatMap(hadnledList);
  };

  const handleChooseSignClick = (signItem: { label: string; value: string }) => {
    operationSign.value = signItem;
  };

  const handleLClickAdd = () => {
    if (props.disabled) {
      return;
    }

    emits('add');
  };

  const handleClickDelete = () => {
    if (props.disabled) {
      return;
    }

    emits('delete');
  };

  defineExpose<Exposes>({
    getValue() {
      return {
        key: titleValue.value,
        method: operationSign.value.value,
        values:
          titleValue.value === 'instance'
            ? contentValue.value.map((item) => {
                const [ip, port] = (item as string).split(':');
                return `${ip}-${port}`;
              })
            : contentValue.value,
      };
    },
  });
</script>
<style lang="less" scoped>
  .dimension-item-main {
    display: flex;
    width: 100%;

    .left-box {
      width: 60px;

      .item-box {
        position: relative;
        width: 44px;
        height: 22px;
        margin-top: 31px;
        font-size: 12px;
        line-height: 22px;
        color: #1768ef;
        text-align: center;
        background: #f0f5ff;
        border-radius: 2px;

        .top-bar {
          position: absolute;
          top: -16px;
          left: 20px;
          width: 0;
          height: 16px;
          border-left: 1px solid #c4c6cc;
        }

        .bottom-bar {
          position: absolute;
          bottom: -15px;
          left: 20px;
          width: 0;
          height: 15px;
          border-left: 1px solid #c4c6cc;
        }
      }

      .other {
        margin-top: 31px;
      }
    }

    .right-box {
      flex: 1;

      .item-box {
        position: relative;
        display: flex;
        width: 100%;
        height: 32px;

        .left-bar {
          position: absolute;
          top: 15px;
          left: -40px;
          width: 40px;
          height: 0;
          border-bottom: 1px solid #c4c6cc;
        }

        .title-box {
          display: flex;
          width: 180px;
          height: 32px;
          background: #fafbfd;
          align-items: center;
          justify-content: space-between;

          .title-select {
            width: 100%;

            :deep(.bk-input) {
              border-radius: 2px 0 0 2px;
            }
          }
        }

        .operaion-sign {
          display: flex;
          height: 32px;
          min-width: 32px;
          padding: 0 10px;
          color: #f59500;
          cursor: pointer;
          border-top: 1px solid #c4c6cc;
          border-bottom: 1px solid #c4c6cc;
          align-items: center;

          &.operaion-sign-disabled {
            cursor: not-allowed;
            background: #fafbfd;
          }
        }

        .content {
          flex: 1;

          :deep(.bk-select-tag-wrapper) {
            gap: 4px;
          }

          .is-focus {
            :deep(.bk-select-tag) {
              border-left-color: #3a84ff;

              &:hover {
                border-left-color: #3a84ff;
              }
            }
          }

          :deep(.bk-input) {
            outline: none;
          }

          :deep(.bk-select-tag) {
            width: 100%;
            min-height: 32px;
            overflow: hidden;
            border-bottom-left-radius: 0;
            border-top-left-radius: 0;

            &:hover {
              border-left-color: #a4a2a2;
            }

            .bk-select-tag-wrapper {
              height: auto;
              max-height: 100px;
              overflow-y: auto;
              gap: 4px;
            }
          }

          .content-custom {
            display: flex;
            width: 100%;

            .condition {
              width: 60px;
              height: 32px;
              line-height: 32px;
              text-align: center;
              border: 1px solid #c4c6cc;
              border-right: none;
            }

            .bk-tag-input {
              flex: 1;

              :deep(.bk-tag-input-trigger) {
                border-radius: 0;
              }
            }
          }
        }

        .operate-box {
          display: flex;
          width: 85px;
          align-items: center;
          padding-left: 12px;

          .plus {
            margin-right: 12px;
          }

          .icon {
            font-size: 18px;
            color: #979ba5;
            cursor: pointer;
          }

          .active-icon {
            color: #979ba5;
          }

          .no-active-icon {
            color: #c4c6cc;
          }
        }
      }
    }
  }
</style>
