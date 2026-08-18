package common

// GetUserNameSql 获取db用户名
var GetUserNameSql = `select USERNAME from dba_users where ACCOUNT_STATUS='OPEN' and `
var GetLongTransactionSql = `SELECT s.sid,
       s.serial#,
       s.username,
       s.machine,
       s.last_call_et,
       s.sql_id
FROM   v$session s
WHERE  s.status IN ('ACTIVE', 'KILLED')
   AND s.type <> 'BACKGROUND'
   AND s.username IN ('IDIP')
   AND s.last_call_et > 600`

var GetUncommittedTransactionSql = `SELECT s.sid,
       s.serial#,
       s.username,
       s.machine,
       s.last_call_et,
       s.prev_sql_id as sql_id
FROM   v$session s,
       v$transaction t
WHERE  s.saddr = t.ses_addr
   AND s.status = 'INACTIVE'
   AND s.username IN ('IDIP')
   AND s.last_call_et > 600`
