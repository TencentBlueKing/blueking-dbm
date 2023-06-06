import _ from 'lodash';
import { useAttrs } from 'vue';

const isCSS = (key: string) => /^(class|style)$/.test(key);
const isListener = (key: string) => /^on[A-Z]/.test(key);

export const useProps = function () {
  const attrs = useAttrs();

  return Object.keys(attrs).reduce((result, key) => {
    if (!isCSS(key)
      && !(isListener(key) && _.isFunction(attrs[key]))) {
      return {
        ...result,
        [key]: attrs[key],
      };
    }
    return result;
  }, {});
};
