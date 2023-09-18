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
  <div class="render-source-box">
    <BkLoading :loading="isLoading">
      <TableEditInput
        ref="editRef"
        v-model="localValue"
        :placeholder="t('请输入管控区域:IP')"
        :rules="rules" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    ref,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getHostTopoInfos } from '@services/ip';

  import { useGlobalBizs } from '@stores';

  import { netIp } from '@common/regex';

  import TableEditInput from '@views/spider-manage/common/edit/Input.vue';

  import type { IDataRow } from './Row.vue';

  interface Props {
    modelValue: IDataRow['source']
  }

  interface Exposes {
    getValue: (field: string) => Promise<string>
  }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const editRef = ref();
  const localValue = ref('');
  const isLoading = ref(false);

  let hostDataMemo = {
    bk_cloud_id: 0,
    bk_host_id: 0,
    ip: '',
  };

  const rules = [
    {
      validator: (value: string) => Boolean(_.trim(value)),
      message: t('源客户端 IP 不能为空'),
    },
    {
      validator: (value: string) => netIp.test(value),
      message: t('源客户端 IP 格式不正确'),
    },
    {
      validator: (value: string) => getHostTopoInfos({
        bk_biz_id: currentBizId,
        filter_conditions: {
          bk_host_innerip: [value],
        },
      }).then((data) => {
        if (data.hosts_topo_info.length < 1) {
          return false;
        }
        const [hostData] = data.hosts_topo_info;
        hostDataMemo = {
          bk_cloud_id: hostData.bk_cloud_id,
          bk_host_id: hostData.bk_host_id,
          ip: hostData.ip,
        };
        return true;
      }),
      message: t('IP不存在'),
    },
  ];

  watch(() => props.modelValue, () => {
    if (!props.modelValue) {
      return;
    }
    hostDataMemo = {
      bk_cloud_id: props.modelValue.cloud_area.id,
      bk_host_id: props.modelValue.host_id,
      ip: props.modelValue.ip,
    };
    localValue.value = `${props.modelValue.cloud_area.id}:${props.modelValue.ip}`;
  }, {
    immediate: true,
  });

  defineExpose<Exposes>({
    getValue() {
      return editRef.value
        .getValue()
        .then(() => ({
          source: hostDataMemo.ip,
          bk_cloud_id: hostDataMemo.bk_cloud_id,
        }));
    },
  });
</script>
<style lang="less" scoped>
  .render-source-box {
    position: relative;
  }
</style>
