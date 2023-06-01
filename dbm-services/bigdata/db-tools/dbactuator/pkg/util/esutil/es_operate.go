package esutil

import (
	"bufio"
	"errors"
	"fmt"
	"os"
	"regexp"
	"strings"

	"dbm-services/bigdata/db-tools/dbactuator/pkg/core/cst"
	"dbm-services/bigdata/db-tools/dbactuator/pkg/util/osutil"
	"dbm-services/common/go-pubpkg/logger"

	"github.com/shirou/gopsutil/mem"
)

// DiskTypePath TODO
type DiskTypePath struct {
	DiskType string // disk type, sd, vd, nvme
	DiskSize string // disk size, 100 bytes
	DiskPath string // eg. /data1, /data
}

// GenerateHeapOption 生成jvm heap size
func GenerateHeapOption(heapsize uint64) []byte {
	rawdata := []byte(fmt.Sprintf(`-Xms%dm
-Xmx%dm`, heapsize, heapsize))
	return rawdata
}

// GetInstHeapByIP 计算单个实例的heap， 单位MB
func GetInstHeapByIP(instCount uint64) (uint64, error) {
	vMem, err := mem.VirtualMemory()
	if err != nil {
		return 0, err
	}
	kilo := uint64(1024)
	totalMemInMi := vMem.Total / kilo / kilo
	EsTotalMem := float64(totalMemInMi) * ratio()
	instHeap := uint64(EsTotalMem) / instCount
	return insMaxHeap(instHeap), nil
}

// ratio TODO
// heap占比系数
func ratio() float64 {
	return 0.6
}

// SupervisorctlUpdate TODO
func SupervisorctlUpdate() error {
	startCmd := "supervisorctl update"
	logger.Info(fmt.Sprintf("exec %s", startCmd))
	_, err := osutil.RunInBG(false, startCmd)
	return err
}

// insMaxHeap 单实例最大heap不超过30g，单位MB
func insMaxHeap(heapSize uint64) uint64 {
	maxHeap := 30720
	if heapSize > uint64(maxHeap) {
		return uint64(maxHeap)
	}
	return heapSize
}

// GetTfByRole 根据角色设置参数
func GetTfByRole(role string) (isMaster bool, isData bool) {
	switch role {
	case cst.EsHot:
		isMaster = false
		isData = true
	case cst.EsCold:
		isMaster = false
		isData = true
	case cst.EsMaster:
		isMaster = true
		isData = false
	case cst.EsClient:
		isMaster = false
		isData = false
	default:
		isMaster = false
		isData = false
	}
	return isMaster, isData
}

// WriteCerToYaml TODO
// es证书配置, /data/esenv/es*/config/elasticsearch.yml
func WriteCerToYaml(filePath, transportPass, httpPass string) error {
	file, err := os.OpenFile(filePath, os.O_WRONLY|os.O_APPEND, 0666)
	if err != nil {
		return err
	}
	// 及时关闭file句柄
	defer file.Close()
	write := bufio.NewWriter(file)
	data := fmt.Sprintf(`opendistro_security.ssl.transport.pemcert_filepath: node1.pem
opendistro_security.ssl.transport.pemkey_filepath: node1.key
opendistro_security.ssl.transport.pemkey_password: %s
opendistro_security.ssl.transport.pemtrustedcas_filepath: root-ca.pem
opendistro_security.ssl.transport.enforce_hostname_verification: false
opendistro_security.ssl.transport.resolve_hostname: false
opendistro_security.ssl.http.enabled: false
opendistro_security.ssl.http.pemcert_filepath: node1_http.pem
opendistro_security.ssl.http.pemkey_filepath: node1_http.key
opendistro_security.ssl.http.pemkey_password: %s
opendistro_security.ssl.http.pemtrustedcas_filepath: root-ca.pem
opendistro_security.nodes_dn:
- CN=node1.bk.com,OU=Ops,O=Bk Com\, Inc.,DC=bk,DC=com
opendistro_security.authcz.admin_dn:
- CN=kirk.bk.com,OU=Ops,O=Bk Com\, Inc.,DC=bk,DC=com
opendistro_security.ssl.http.clientauth_mode: OPTIONAL
opendistro_security.allow_unsafe_democertificates: true
opendistro_security.enable_snapshot_restore_privilege: true
opendistro_security.check_snapshot_restore_write_privileges: true
opendistro_security.restapi.roles_enabled: ["all_access", "security_rest_api_access"]`, transportPass, httpPass)

	write.WriteString(data)
	write.Flush()
	return nil
}

// GenEsini TODO
func GenEsini(seqNum uint64) []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:elasticsearch%d]
command=/data/esenv/es_%d/bin/elasticsearch ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/eslog%d/es_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`, seqNum, seqNum, seqNum))
	return iniRaw
}

// GenKibanaini TODO
func GenKibanaini() []byte {
	iniRaw := []byte(`[program:kibana]
command=/data/esenv/kibana/bin/kibana -c /data/esenv/kibana/config/kibana.yml ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=10 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/esenv/kibana/kibana_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`)
	return iniRaw
}

// GenInfluxdbini TODO
func GenInfluxdbini() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:influxdb]
command=/data/influxdbenv/influxdb/usr/bin/influxd -config /data/influxdbenv/influxdb/etc/influxdb/influxdb.conf ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=influxdb ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/influxdblog/influxdb_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`))
	return iniRaw
}

// GenTelegrafini TODO
func GenTelegrafini() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:telegraf]
command=/data/influxdbenv/telegraf/usr/bin/telegraf --config /data/influxdbenv/telegraf/etc/telegraf/telegraf.conf ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=influxdb ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/influxdbenv/telegraf/telegraf_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`))
	return iniRaw
}

// GenKafkaini TODO
func GenKafkaini() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:kafka]
command=/data/kafkaenv/kafka/bin/kafka-server-scram-start.sh /data/kafkaenv/kafka/config/server.properties ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/kafkalog/kafka_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`))
	return iniRaw
}

// GenZookeeperini TODO
func GenZookeeperini() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:zookeeper]
command=/data/kafkaenv/zk/bin/zkServer.sh start-foreground ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
stopsignal=KILL ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/zklog/zk_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`))
	return iniRaw
}

// GenManagerini TODO
func GenManagerini() []byte {
	iniRaw := []byte(fmt.Sprintf(`[program:manager]
command=/data/kafkaenv/cmak-3.0.0.5/bin/cmak -java-home /data/kafkaenv/jdk11 ; the program (relative uses PATH, can take args)
numprocs=1 ; number of processes copies to start (def 1)
autostart=true ; start at supervisord start (default: true)
startsecs=3 ; # of secs prog must stay up to be running (def. 1)
startretries=99 ; max # of serial start failures when starting (default 3)
autorestart=true ; when to restart if exited after running (def: unexpected)
exitcodes=0 ; 'expected' exit codes used with autorestart (default 0,2)
user=mysql ;
stopsignal=KILL ;
redirect_stderr=true ; redirect proc stderr to stdout (default false)
stdout_logfile=/data/kafkaenv/cmak-3.0.0.5/manager_startup.log ; stdout log path, NONE for none; default AUTO
stdout_logfile_maxbytes=50MB ; max # logfile bytes b4 rotation (default 50MB)
stdout_logfile_backups=10 ; # of stdout logfile backups (default 10)`))
	return iniRaw
}

// GetInstMem TODO
func GetInstMem() (uint64, error) {
	vMem, err := mem.VirtualMemory()
	if err != nil {
		return 0, err
	}
	kilo := uint64(1024)
	totalMemInMi := vMem.Total / kilo / kilo
	return totalMemInMi, nil
}

// ToMasterStr TODO
func ToMasterStr(ips []string) string {
	for a, ip := range ips {
		ips[a] = fmt.Sprintf("master-%s_1", ip)
	}
	return strings.Join(ips[:], ",")
}

// NodeToProcess TODO
func NodeToProcess(node string) (process string) {
	id, _ := GetNumByNode(node)
	switch node {
	case "all":
		process = "all"
	case id:
		process = fmt.Sprintf("elasticsearch%s", id)
	default:
		process = "all"
	}
	return process
}

// GetNumByNode TODO
func GetNumByNode(node string) (string, error) {
	if node == "all" || len(node) == 0 {
		return "all", nil
	}
	reg := regexp.MustCompile(`\w.*-\w.*_(\d)`)
	if reg == nil {
		return "", errors.New("regexp complie error")
	}
	result := reg.FindAllStringSubmatch(node, -1)
	id := result[0][1]
	return fmt.Sprintf("elasticsearch%s", id), nil
}

// GetEsLocalIp TODO
func GetEsLocalIp() (ip string, err error) {
	extraCmd := fmt.Sprintf(`grep -w 'network.host'  %s|awk '{print $1}'`, cst.DefaultEsConfigFile)
	logger.Info("cmd, [%s]", extraCmd)
	outputs, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return "", err
	}
	logger.Info("local ip %s", outputs)
	ip = strings.TrimSuffix(outputs, "\n")
	return ip, nil
}

// GetEsLocalPorts TODO
func GetEsLocalPorts() (ports []string, err error) {
	extraCmd := fmt.Sprintf(`grep -w 'http.port' %s/es_*/config/elasticsearch.yml|awk '{print $2}'`, cst.DefaulEsEnv)
	logger.Info("cmd, [%s]", extraCmd)
	outputs, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Error("[%s] execute failed, %v", extraCmd, err)
		return nil, err
	}
	trimRes := strings.TrimSuffix(outputs, "\n")
	ports = strings.Fields(trimRes)
	return ports, nil
}

// GetPath return paths array according to df -h result
func GetPath() []string {
	var paths []string
	var disks []DiskTypePath
	typeCount := make(map[string]int)
	/*
		Filesystem     1K-blocks      Used Available Use% Mounted on
		devtmpfs         8047192         0   8047192   0% /dev
		tmpfs            8062512         0   8062512   0% /dev/shm
		tmpfs            8062512    280236   7782276   4% /run
		tmpfs            8062512         0   8062512   0% /sys/fs/cgroup
		/dev/vda1      103079844  22737932  76047608  24% /
		/dev/vdb1      412715432 165966836 225760744  43% /data
		tmpfs            1612500         0   1612500   0% /run/user/0
	*/
	extraCmd := `df | grep ^/dev |egrep -vw '/|/usr|/boot'|awk '{print $1":"$2":"$NF}'`
	logger.Info("Command [%s]", extraCmd)
	output, err := osutil.ExecShellCommand(false, extraCmd)
	if err != nil {
		logger.Info("[%s] execute failed, %s", extraCmd, err.Error())
		return paths
	}
	logger.Info("Commnad output, %s", output)
	op := strings.TrimSuffix(output, "\n")
	if len(op) == 0 {
		logger.Info("No independent disk found")
		return paths
	}

	var dd DiskTypePath
	diskList := strings.Split(op, "\n")
	logger.Info("DiskList %+v", diskList)
	for _, d := range diskList {
		diskType := GetDiskType(strings.Split(d, ":")[0])
		diskSize := strings.Split(d, ":")[1]
		diskPath := strings.Split(d, ":")[2]
		typeCount[diskType]++
		dd = DiskTypePath{
			DiskType: diskType,
			DiskSize: diskSize,
			DiskPath: diskPath,
		}
		disks = append(disks, dd)
	}

	logger.Info("disks %+v", disks)
	if len(typeCount) == 1 {
		logger.Info("May be all disks has same size and type")
		for _, x := range disks {
			paths = append(paths, x.DiskPath)
		}
	}

	if len(typeCount) == 2 {
		logger.Info("There are 2 different type of disks")
		biggerDisk := MaxCountDisk(typeCount)
		for _, x := range disks {

			if x.DiskType == biggerDisk {
				paths = append(paths, x.DiskPath)
			}
		}

	}

	if len(typeCount) > 2 {
		logger.Info("More than 2 type of diks,can't handel it")
		for _, x := range disks {
			paths = append(paths, x.DiskPath)
		}
	}

	return paths

}

// GetDiskType getdisktype
func GetDiskType(disk string) string {
	var dtype string
	switch {
	case strings.Contains(disk, "vd"):
		dtype = "vd"
	case strings.Contains(disk, "sd"):
		dtype = "sd"
	case strings.Contains(disk, "nvme"):
		dtype = "nvme"
	default:
		dtype = ""
	}
	return dtype
}

// MaxCountDisk return max count disk type
func MaxCountDisk(m map[string]int) string {
	var maxKey string
	var maxVal int

	for maxKey, maxVal = range m {
		break
	}
	for x, y := range m {
		if y > maxVal {
			maxKey = x
		}
	}
	return maxKey
}

// GenPath get paths from num
func GenPath(seq int, seed int, diskPath []string) []string {
	var paths []string
	start := (seq - 1) * seed
	end := start + seed - 1
	for s := start; s <= end; s++ {
		paths = append(paths, diskPath[s])
	}
	return paths
}
