PID=$(pgrep -x 'mysql-crond' 2>/dev/null)
if [ $? -eq 0 ];then
  kill -9 $PID
fi