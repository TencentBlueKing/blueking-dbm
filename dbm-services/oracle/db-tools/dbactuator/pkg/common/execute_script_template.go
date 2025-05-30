package common

// ExecuteScriptTemplate 执行sql脚本模板
var ExecuteScriptTemplate = `
#!/bin/sh
set -e
. $HOME/.bash_profile
echo "db_pkg_script_start" > {{logPath}}
sqlplus {{dbUser}}/{{dbUserPassword}}@LOCALDB <<EOF
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
