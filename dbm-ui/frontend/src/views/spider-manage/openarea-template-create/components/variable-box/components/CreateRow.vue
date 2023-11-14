<template>
  <tbody>
    <td style="padding: 0">
      <TableEditInput
        ref="nameRef"
        v-model="formData.name"
        :rules="nameRules" />
    </td>
    <td style="padding: 0">
      <TableEditInput
        ref="descRef"
        v-model="formData.desc"
        :rules="descRules" />
    </td>
    <td>
      String
    </td>
    <td>
      <BkButton
        :loading="isSubmiting"
        text
        theme="primary"
        @click="handleSubmit">
        {{ t('保存') }}
      </BkButton>
      <BkButton
        class="ml-4"
        text
        theme="primary">
        {{ t('取消') }}
      </BkButton>
    </td>
  </tbody>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { reactive } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import {
    updateBizSetting,
  } from '@services/system-setting';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@components/tools-table-input/index.vue';

  import { messageSuccess } from '@utils';

  import type { IVariable } from '../Index.vue';

  interface Props {
    index: number
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const list = defineModel<IVariable[]>('list', {
    local: true,
    required: true,
  });

  const nameRef = ref<InstanceType<typeof TableEditInput>>();
  const descRef = ref<InstanceType<typeof TableEditInput>>();
  const isSubmiting = ref(false);
  const formData = reactive({
    name: '',
    desc: '',
    builtin: false,
  });

  const nameRules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('变量名不能为空'),
    },
    {
      validator: (value: string) => _.every(list.value, item => item.name !== value),
      message: t('变量名重复'),
    },
  ];
  const descRules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('变量说明不能为空'),
    },
  ];

  const {
    run: updateVariableList,
  } = useRequest(updateBizSetting, {
    manual: true,
    onSuccess() {
      const lastVariableList = [...list.value];
      lastVariableList.splice(props.index, 1, formData);
      list.value = lastVariableList;
      messageSuccess('添加变量成功');
    },
  });

  const handleSubmit = () => {
    isSubmiting.value = true;
    Promise.all([
      (nameRef.value as InstanceType<typeof TableEditInput>).getValue(),
      (descRef.value as InstanceType<typeof TableEditInput>).getValue(),
    ]).then(() => {
      const lastVariableList = _.filter(list.value, item => ((item.name && item.desc) || item.builtin));
      lastVariableList.push(formData);
      return updateVariableList({
        bk_biz_id: currentBizId,
        key: 'OPEN_AREA_VARS',
        value: lastVariableList,
      });
    })
      .finally(() => {
        isSubmiting.value = false;
      });
  };
</script>

