set -e
COUNTER=$1
for IDX in `seq 1 $COUNTER`
do
  echo "$IDX: $(date)"
  sleep 1
done