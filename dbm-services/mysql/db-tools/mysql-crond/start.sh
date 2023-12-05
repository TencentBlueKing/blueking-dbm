SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd $SCRIPT_DIR && nohup ./mysql-crond ${@:1} 1>/dev/null 2>start-crond.err &