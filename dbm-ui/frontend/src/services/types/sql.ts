import SemanticData from '@services/model/sql-import/semantic-data';

export interface QuerySemanticDataResult {
  import_mode: string;
  semantic_data: SemanticData;
  sql_data_ready: boolean;
}
