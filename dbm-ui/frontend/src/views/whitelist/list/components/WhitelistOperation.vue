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
  <DbDialog
    v-model:is-show="isShow"
    :cancel-handler="handleCancel"
    :confirm-handler="handleSubmit"
    :esc-close="false"
    :quick-close="false"
    :title="title"
    :width="640">
    <DbForm
      ref="formRef"
      class="mb-20"
      form-type="vertical"
      :model="formdata">
      <BkFormItem
        ref="ipRef"
        :label="t('IP地址')"
        property="ips"
        required
        :rules="ipRules">
        <BkInput
          v-model="formdata.ips"
          :placeholder="placeholder"
          :rows="8"
          type="textarea"
          @input="debounceInput" />
      </BkFormItem>
      <BkFormItem
        :label="t('备注')"
        property="remark"
        required>
        <BkInput
          v-model="formdata.remark"
          :placeholder="t('请添加IP的简要说明_如IP用途等')"
          style="height: 114px"
          type="textarea" />
      </BkFormItem>
    </DbForm>
  </DbDialog>
  <div style="display: none">
    <div
      ref="mergeTipsRef"
      class="merge-tips"
      style="padding: 4px; font-size: 12px; color: #63656e">
      <p class="pb-12">
        {{ t('检测到多个前缀相同的IP_是否立即合并成以下IP') }}
      </p>
      <p
        v-for="ip in ipMergeState.mergeValues"
        :key="ip">
        {{ ip }}
      </p>
      <div class="pt-12">
        <BkButton
          text
          theme="primary"
          @click="handleMerge">
          {{ t('合并') }}
        </BkButton>
        <span
          class="inline-block"
          style="transform: scale(0.8)">
          ｜
        </span>
        <BkButton
          text
          theme="primary"
          @click="handleNoMerge">
          {{ t('不合并') }}
        </BkButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { useI18n } from 'vue-i18n';

  import { createWhitelist, getWhitelist, updateWhitelist } from '@services/source/whitelist';

  import { batchSplitRegex, ipv4 } from '@common/regex';

  import { messageSuccess } from '@utils';

  type WhitelistItem = ServiceReturnType<typeof getWhitelist>['results'][number];

  type Emits = (e: 'successed') => void;

  interface Props {
    bizId: number;
    data: WhitelistItem;
    isEdit: boolean;
    title: string;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const { t } = useI18n();

  const placeholder = t('白名单输入框编辑提示');
  const formRef = ref();
  const mergeTipsRef = ref();
  const ipRef = ref();
  const formdata = reactive({
    ips: '',
    remark: '',
  });
  let mergeInst: Instance | undefined = undefined;
  const ipMergeState = reactive({
    ignoreValues: [] as string[],
    mergeValues: [] as string[],
    renderValues: [] as string[],
  });

  const resetFormState = () => {
    formRef.value.clearValidate();

    setTimeout(() => {
      formdata.ips = '';
      formdata.remark = '';
      const keys = Object.keys(ipMergeState) as Array<keyof typeof ipMergeState>;
      for (const key of keys) {
        ipMergeState[key] = [];
      }
    }, 300);
  };

  const ipRules = [
    {
      message: t('ip中存在格式错误'),
      trigger: 'blur',
      validator: (value: string) =>
        _.every(value.split(batchSplitRegex), (item) => {
          const text = _.trim(item);
          if (!text) {
            return true;
          }
          return (
            ipv4.test(text) ||
            text === 'localhost' ||
            text === '%' ||
            /^(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)(?:\.(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]\d|\d)){0,2}(\.%)$/.test(text)
          );
        }),
    },
  ];

  watch(
    isShow,
    (show) => {
      if (show && props.isEdit) {
        formdata.remark = props.data.remark;
        formdata.ips = props.data.ips.join('\n');
      }
    },
    { immediate: true },
  );

  const renderTips = () => {
    handleHideMergeInst();

    if (mergeTipsRef.value && ipRef.value.$el) {
      mergeInst = tippy(ipRef.value.$el as SingleTarget, {
        appendTo: 'parent',
        arrow: true,
        content: mergeTipsRef.value,
        hideOnClick: false,
        interactive: true,
        maxWidth: 'none',
        offset: [0, 8],
        placement: 'left',
        theme: 'light',
        trigger: 'manual',
        zIndex: 999999,
      });

      mergeInst.show();
    }
  };

  // 没有达到数量的 IP 不进行合并
  const resolveMergeIpMap = (ipMap: Map<string, string[]>, ips: string[], limit = 2) => {
    const entries = ipMap.entries();
    for (const [ip, values] of entries) {
      if (values.length <= limit) {
        ips.push(...values);
        ipMap.delete(ip);
      }
    }
  };

  const debounceInput = _.debounce((value: string) => {
    ipMergeState.mergeValues = [];
    ipMergeState.renderValues = [];

    const ips = value.split('\n').filter((ip) => ip.trim());
    // 记录相同 aaa.bbb.ccc.% 的 ip
    const abcIpMap = new Map<string, string[]>();
    for (const ip of ips) {
      // 不通过 ip 校验的则直接回填，不修改用户内容
      if (!ipv4.test(ip)) {
        ipMergeState.renderValues.push(ip);
        continue;
      }

      // 修改为 aaa.bbb.ccc.%
      const abcIp = `${ip.slice(0, ip.lastIndexOf('.'))}.%`;
      // 修改为 aaa.bbb.%
      const abIp = `${abcIp.slice(0, abcIp.slice(0, -2).lastIndexOf('.'))}.%`;
      // 处理上次忽略合并的 IP
      if (ipMergeState.ignoreValues.includes(abcIp) || ipMergeState.ignoreValues.includes(abIp)) {
        ipMergeState.renderValues.push(ip);
        continue;
      }
      abcIpMap.set(abcIp, (abcIpMap.get(abcIp) || []).concat([ip]));
    }
    resolveMergeIpMap(abcIpMap, ipMergeState.renderValues);

    // 记录相同 aaa.bbb.% 的 ip
    const abIpMap = new Map<string, string[]>();
    for (const abcIp of abcIpMap.keys()) {
      // 修改为 aaa.bbb.%
      const abIp = `${abcIp.slice(0, abcIp.slice(0, -2).lastIndexOf('.'))}.%`;
      abIpMap.set(abIp, (abIpMap.get(abIp) || []).concat([abcIp]));
    }
    resolveMergeIpMap(abIpMap, ipMergeState.mergeValues);

    // 区分 aaa.bbb.ccc.% 与 aaa.bbb.%
    for (const [ip, values] of abIpMap.entries()) {
      // 不需要进一步合并
      if (value.length <= 2) {
        ipMergeState.mergeValues.push(...values);
        continue;
      }
      ipMergeState.mergeValues.push(ip);
    }

    if (ipMergeState.mergeValues.length > 0) {
      renderTips();
    }
  }, 200);

  const handleHideMergeInst = () => {
    if (mergeInst) {
      mergeInst.hide();
      mergeInst.unmount();
      mergeInst.destroy();
      mergeInst = undefined;
    }
  };

  const handleNoMerge = () => {
    ipMergeState.ignoreValues.push(...ipMergeState.mergeValues);
    handleHideMergeInst();
  };

  const handleMerge = () => {
    formdata.ips = [...ipMergeState.renderValues, ...ipMergeState.mergeValues].join('\n');
    handleHideMergeInst();
  };

  const handleCancel = () => {
    resetFormState();
    return Promise.resolve();
  };

  const handleSubmit = () => {
    return formRef.value.validate().then(() => {
      const api = props.isEdit ? updateWhitelist : createWhitelist;

      return api({
        bk_biz_id: props.bizId,
        id: props.data?.id || 0,
        ips: _.uniq(formdata.ips.split(batchSplitRegex)),
        remark: formdata.remark,
      }).then(() => {
        messageSuccess(t('创建成功'));
        resetFormState();
        emits('successed');
      });
    });
  };
</script>
