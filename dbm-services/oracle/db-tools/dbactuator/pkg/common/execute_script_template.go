package common

// ExecuteScriptTemplate 执行sql脚本模板
var ExecuteScriptTemplate = `
#!/bin/sh
. $HOME/.bash_profile
echo "db_pkg_script_start" > {{logPath}}
sqlplus /nolog <<EOF
connect {{dbUser}}/{{dbUserPassword}}@LOCALDB
set timing on;
set time on;
set echo on;
spool {{logPath}} append
WHENEVER SQLERROR EXIT SQL.SQLCODE;
{{executeScriptFormat}}
commit;
spool off;
exit
EOF
`
