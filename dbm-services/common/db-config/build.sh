
workDir=`pwd`

# unit test
cd internal/service/simpleconfig && go test -v . ;cd  $workDir
cd internal/repository/model && go test -v . ; cd $workDir
cd pkg/validate && go test -v . ;cd  $workDir

cd  $workDir
./build_doc.sh
make
pkill bkconfigsvr
kill `cat svr.pid`
sleep 0.5
./bkconfigsvr >>logs/main.log 2>&1 &
echo $! > svr.pid
sleep 0.5
ps -ef|grep bkconfigsvr|grep -v grep