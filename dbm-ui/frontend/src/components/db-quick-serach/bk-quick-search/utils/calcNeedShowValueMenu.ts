import _ from 'lodash';

import type { Props } from '../Index.vue';

export const calcNeedShowValueMenu = (data: Props['data'][number]) => {
  if (data.type || data.component) {
    return true;
  }

  if (_.isArray(data.list)) {
    return true;
  }

  if (_.isFunction(data.remoteMethod)) {
    return true;
  }

  return false;
};
