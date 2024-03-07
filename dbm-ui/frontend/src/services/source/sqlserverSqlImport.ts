import GrammarCheckModel from '@services/model/sql-import/grammar-check';

import http from '../http';

/**
 * sql 语法检测
 */
export function grammarCheck(params: FormData) {
  return http
    .post(`/apis/sqlserver/bizs/${window.PROJECT_CONFIG.BIZ_ID}/sql_import/grammar_check/`, params)
    .then((data) =>
      Object.keys(data).reduce(
        (result, key) => ({
          ...result,
          [key]: new GrammarCheckModel(data[key]),
        }),
        {} as Record<string, GrammarCheckModel>,
      ),
    );
}
