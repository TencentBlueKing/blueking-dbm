import {
  createApp,
} from 'vue';

import type ApplyDataModel from '@services/model/iam/apply-data';

import PermissionDialog, {
  type CheckParams,
} from '@components/apply-permission/dialog.vue';

import i18n from '@locales/index';

export const permissionDialog = (applyData?: ApplyDataModel, checkParams?: CheckParams) => {
  const container = document.createElement('div');
  const handleCancel = () => {
    (container.parentNode as HTMLElement).removeChild(container);
  };
  const app = createApp({
    setup() {
      return () => (
        <PermissionDialog
          applyData={applyData}
          checkParams={checkParams}
          onCancel={handleCancel} />
      );
    },
  });
  app.use(i18n).mount(container);
  document.body.appendChild(container);
};
