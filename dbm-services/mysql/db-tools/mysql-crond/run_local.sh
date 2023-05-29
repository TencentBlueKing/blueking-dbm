VERSION_FLAG="-X main.version=`date +'%y%m%d.%H.%M'`"
STAMP_FLAG="-X main.buildStamp='`date -u '+%Y-%m-%d_%I:%M:%S%p'`"
GIT_FLAG="-X main.gitHash='`git rev-parse HEAD`'"


go run -ldflags "${VERSION_FLAG} ${STAMP_FLAG} ${GIT_FLAG}" main.go ${@: 1}