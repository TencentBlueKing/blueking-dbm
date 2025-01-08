
example1:
```
// performance_schema = ON
// performance_schema_digests_size = 10000
// performance_schema_max_digest_length = 1024
// performance_schema_max_sql_text_length = 1024

mysql> select * from performance_schema.setup_consumers;
+----------------------------------+---------+
| NAME                             | ENABLED |
+----------------------------------+---------+
| events_stages_current            | NO      |
| events_stages_history            | NO      |
| events_stages_history_long       | NO      |
| events_statements_current        | YES     |
| events_statements_history        | YES     |
| events_statements_history_long   | NO      |
| events_transactions_current      | NO      |
| events_transactions_history      | NO      |
| events_transactions_history_long | NO      |
| events_waits_current             | NO      |
| events_waits_history             | NO      |
| events_waits_history_long        | NO      |
| global_instrumentation           | YES     |
| thread_instrumentation           | YES     |
| statements_digest                | YES     |
+----------------------------------+---------+
```

example2:
```
                SCHEMA_NAME: ceiba_admin_pro
                     DIGEST: 09ec094394a7af2af3230110f87a5bbd
                DIGEST_TEXT: SELECT * FROM `t_data_source`
                 COUNT_STAR: 133
             SUM_TIMER_WAIT: 30786417000
             MIN_TIMER_WAIT: 120668000
             AVG_TIMER_WAIT: 231476000
             MAX_TIMER_WAIT: 399896000
              SUM_LOCK_TIME: 14579000000
                 SUM_ERRORS: 0
               SUM_WARNINGS: 0
          SUM_ROWS_AFFECTED: 0
              SUM_ROWS_SENT: 133
          SUM_ROWS_EXAMINED: 133
SUM_CREATED_TMP_DISK_TABLES: 0
     SUM_CREATED_TMP_TABLES: 0
       SUM_SELECT_FULL_JOIN: 0
 SUM_SELECT_FULL_RANGE_JOIN: 0
           SUM_SELECT_RANGE: 0
     SUM_SELECT_RANGE_CHECK: 0
            SUM_SELECT_SCAN: 133
      SUM_SORT_MERGE_PASSES: 0
             SUM_SORT_RANGE: 0
              SUM_SORT_ROWS: 0
              SUM_SORT_SCAN: 0
          SUM_NO_INDEX_USED: 133
     SUM_NO_GOOD_INDEX_USED: 0
                 FIRST_SEEN: 2022-08-23 11:47:13
                  LAST_SEEN: 2024-12-17 17:35:36
```