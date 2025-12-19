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
  <BkFormItem
    error-display-type="tooltips"
    error-tip-append-to-parent
    :label="t('查询 DB')"
    property="dbname"
    required
    :rules="rules"
    style="width: 750px">
    <div style="display: none">
      <div
        ref="pop"
        style="font-size: 12px; line-height: 24px; color: #63656e">
        <div class="db-table-tag-tip">
          <div style="font-weight: 700">{{ t('库表输入说明') }}：</div>
          <div>
            <div class="circle-dot"></div>
            <span>{{ t('不允许输入系统库，如"master", "msdb", "model", "tempdb", "Monitor"') }}</span>
          </div>
          <div>
            <div class="circle-dot"></div>
            <span>{{ t('DB名、表名不允许为空，忽略DB名、忽略表名不允许为 *') }}</span>
          </div>
          <div>
            <div class="circle-dot"></div>
            <span>{{ t('支持 %（指代任意长度字符串）,*（指代全部）2个通配符') }}</span>
          </div>
          <div>
            <div class="circle-dot"></div>
            <span>{{ t('单元格可同时输入多个对象，使用换行，空格或；，｜分隔，按 Enter 或失焦完成内容输入') }}</span>
          </div>
          <div>
            <div class="circle-dot"></div>
            <span>{{ t('包含通配符时, 每一单元格只允许输入单个对象。% 不能独立使用， * 只能单独使用') }}</span>
          </div>
        </div>
      </div>
    </div>
    <div
      ref="root"
      @click="handleShowTips">
      <BkLoading :loading="isLoading">
        <BkInput
          v-model="modelValue"
          :placeholder="t('请输入 DB 名称，支持通配符_%_，含通配符的仅支持单个')" />
      </BkLoading>
    </div>
  </BkFormItem>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { batchCheckClusterDatabase } from '@services/source/dbbase';

  interface Props {
    clusterIds: number[];
    clusterMap: Record<
      string,
      {
        master_domain: string;
      }
    >;
    validateMaster?: boolean;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const { t } = useI18n();

  const rootRef = useTemplateRef('root');
  const popRef = useTemplateRef('pop');

  let tippyIns: Instance | undefined;
  const isLoading = ref(false);

  const systemDbNames = ['msdb', 'model', 'tempdb', 'Monitor'].concat(props.validateMaster ? ['master'] : []);

  const rules = [
    {
      message: t('不允许输入系统库和特殊库 n', { n: systemDbNames.join(',') }),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => !systemDbNames.includes(item)),
    },
    {
      message: t('有 master 时只允许一个'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (!props.validateMaster) {
          return true;
        }
        return !(value.includes('master') && value.length > 1);
      },
    },
    {
      message: t('* 只能独立使用'),
      trigger: 'change',
      validator: (value: string[]) => !_.some(value, (item) => /\*/.test(item) && item.length > 1),
    },
    {
      message: t('% 不允许单独使用'),
      trigger: 'change',
      validator: (value: string[]) => _.every(value, (item) => !/^%$/.test(item)),
    },
    {
      message: t('含通配符的单元格仅支持输入单个对象'),
      trigger: 'change',
      validator: (value: string[]) => {
        if (_.some(value, (item) => /[*%?]/.test(item))) {
          return value.length < 2;
        }
        return true;
      },
    },
    {
      message: '',
      trigger: 'blur',
      validator: (value: string) => {
        if (!value) {
          return true;
        }
        // % 通配符不需要校验不存在
        const clearDbList = _.filter(value, (item) => !/[*%]/.test(item));
        if (clearDbList.length < 1) {
          return true;
        }
        if (!props.clusterIds.length) {
          return t('请先输入集群');
        }
        isLoading.value = true;
        return batchCheckClusterDatabase({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          cluster_ids: props.clusterIds,
          db_list: [value],
        }).then((data) => {
          isLoading.value = false;
          const clusterNotExistDb = props.clusterIds.reduce<string[]>((result, clusterId) => {
            if (!data[clusterId][value]) {
              result.push(props.clusterMap[clusterId].master_domain);
            }
            return result;
          }, []);
          if (clusterNotExistDb.length > 0) {
            return t('集群xx 不存在该 DB', [clusterNotExistDb.join('、')]);
          }
          return true;
        });
      },
    },
  ];

  const handleShowTips = () => {
    tippyIns?.show();
  };

  onMounted(() => {
    setTimeout(() => {
      if (rootRef.value && popRef.value) {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          appendTo: () => document.body,
          arrow: true,
          content: popRef.value,
          hideOnClick: true,
          interactive: true,
          maxWidth: 'none',
          offset: [0, 8],
          placement: 'top',
          theme: 'light',
          trigger: 'manual',
          zIndex: 9998,
        });
      }
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>

<style lang="less" scoped>
  .db-table-tag-tip {
    display: flex;
    padding: 3px 7px;
    line-height: 24px;
    flex-direction: column;

    div {
      display: flex;
      align-items: center;

      .circle-dot {
        display: inline-block;
        width: 4px;
        height: 4px;
        margin-right: 6px;
        background-color: #63656e;
        border-radius: 50%;
      }
    }
  }
</style>
