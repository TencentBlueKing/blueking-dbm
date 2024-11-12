package atomredis

import (
	"dbm-services/redis/db-tools/dbactuator/models/myredis"
	"dbm-services/redis/db-tools/dbactuator/pkg/consts"
	"dbm-services/redis/db-tools/dbactuator/pkg/jobruntime"
	"dbm-services/redis/db-tools/dbactuator/pkg/util"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"
	"time"
)

/*
 本地重建slave ， Cache 仅限版本使用
 场景：
 1. 已经是slave了， 强制重建 ，从master 重新同步数据过来
 2. 复用故障恢复后的机器，重新从master 重新同步数据
	分以前是slave角色， 和以前是master角色
*/

// RedisLocalDoDR 本地重建slave
type RedisLocalDoDR struct {
	DataDir   string
	startTime int64
	Err       error `json:"-"`
	params    RedisLocalDoDRParams
	runtime   *jobruntime.JobGenericRuntime
}

/*{
	"bk_biz_id":0,
	"cluster_id":111,
	"cluster_type":"TwemproxyRedisInstance",
	"immute_domain":"x.1.x.db",
	"instances":[
		"master_ip":"","master_port":30000,
		"slave_ip":"","slave_port":30000,
	]
}*/

// Init implements jobruntime.JobRunner.
func (r *RedisLocalDoDR) Init(runtime *jobruntime.JobGenericRuntime) error {
	// 获取安装参数
	r.DataDir = consts.GetRedisDataDir()
	r.runtime = runtime
	r.runtime.Logger.Info("start to redis local do dr . with dir :%s", r.DataDir)

	// 加载参数
	if err := json.Unmarshal([]byte(r.runtime.PayloadDecoded), &r.params); err != nil {
		err = fmt.Errorf("%s:get parameters fail by json.Unmarshal, error:%v", r.Name(), err)
		r.runtime.Logger.Error(err.Error())
		return err
	}

	x, _ := json.Marshal(r.params)
	r.runtime.Logger.Info("loaded params :%s", x)

	return nil
}

/*
	1. if redis login
	  - role must be slave .
			- run.master_host = master_ip & run.master_port = master_port
				- do bgsave & shutdown
			- run.master_host != master_ip & reset_master = True
				- goto  ==> 2.
		- mv rdb , aof .
		- sed config  &  start  & slaveof master_ip master_port
		- waiting master_link_up

		2. redis can't login
	   - mv rdb, aof .
		- sed config  &  start  & slaveof master_ip master_port
		 - waiting master_link_up

		 3. stop dbmon. call script /stop.sh
*/
// Run implements jobruntime.JobRunner.
func (r *RedisLocalDoDR) Run() error {
	if r.params.ClusterType != consts.TendisTypeTwemproxyRedisInstance &&
		r.params.ClusterType != consts.TendisTypeRedisInstance {
		r.runtime.Logger.Error("Unexpected clustertype <%s>", r.params.ClusterType)
		return fmt.Errorf("X-%s-X", r.params.ClusterType)
	}

	r.runtime.Logger.Warn("first stop dbmon.")
	if rst, err := util.RunBashCmd("/home/mysql/bk-dbmon/stop.sh", "", nil, 10*time.Second); err != nil {
		r.runtime.Logger.Warn("try stop dbmon failed %s:+%+v", rst, err)
	}
	defer func() {
		r.runtime.Logger.Warn("finally start dbmon.")
		if rst, err := util.RunBashCmd("/home/mysql/bk-dbmon/start.sh", "", nil, 10*time.Second); err != nil {
			r.runtime.Logger.Error("try start dbmon failed %s:+%+v", rst, err)
		}
	}()

	r.startTime = time.Now().Unix()
	for idx, instance := range r.params.Instances {
		addr := fmt.Sprintf("%s:%d", instance.SlaveIP, instance.SlavePort)
		r.runtime.Logger.Info("begin local redo dr %d:%s", idx, addr)
		password, err := myredis.GetRedisPasswdFromConfFile(instance.SlavePort)
		if err != nil {
			r.runtime.Logger.Error("get instance password failed %d:%s", instance.SlavePort, err)
			return err
		}

		//check & shutdown
		if err := r.tryLoginAndShutdown(addr, password, idx, instance); err != nil {
			return err
		}

		// MV 数据文件 - mv rdb, aof .
		// sed -i 's/slaveof /#slaveof /g' redis.conf instance.conf
		if err := r.backupFiles(addr, instance); err != nil {
			return err
		}
		// start , slaveof ,==,rewirte
		if err := r.startAndWetLinkUp(addr, password, idx, instance); err != nil {
			return err
		}
		r.runtime.Logger.Info("done local redo dr %d:%s ^_^ \n", idx, addr)
	}
	return nil
}

// start-redis.sh
// slaveof master xxx xx
// config rewite
// == for link up .
func (r *RedisLocalDoDR) startAndWetLinkUp(addr, pass string, idx int, instance ReplicaItem) error {
	if rst, err := util.RunBashCmd(fmt.Sprintf("/usr/local/redis/bin/start-redis.sh %d",
		instance.SlavePort), "", nil, 10*time.Second); err != nil || rst != "" {
		r.runtime.Logger.Error("start redis failed ?? %d:%s:%s:%+v", idx, addr, rst, err)
		return fmt.Errorf("r:%s:e:%+v", rst, err)
	}

	rConn, err := myredis.NewRedisClientWithTimeout(addr, pass, 0, r.params.ClusterType, time.Second*10)
	if err != nil {
		r.runtime.Logger.Warn("connect instance failed %d:%s:%+v", idx, addr, err)
		return err
	}
	defer rConn.Close()

	if _, err := rConn.ConfigSet("masterauth", pass); err != nil {
		r.runtime.Logger.Warn("config set instance masterauth failed %d:%s:%s:%+v", idx, addr, pass, err)
		return err
	}
	if _, err := rConn.SlaveOf(instance.MasterIP, strconv.Itoa(instance.MasterPort)); err != nil {
		r.runtime.Logger.Warn("slaveof 2 %s:%d failed %d:%s:%s:%+v",
			instance.MasterIP, instance.MasterPort, idx, addr, pass, err)
		return err
	}

	// wait and rewrite config.
	if err := r.WaitMasterLinkUp(rConn, addr); err != nil {
		return err
	}
	return nil
}

// CreateReplicaAndWait slaveof and wait util status==up
func (r *RedisLocalDoDR) WaitMasterLinkUp(rConn *myredis.RedisClient, addr string) error {
	i, maxWait := 0, 200
	for {
		i++
		iimap, err := rConn.Info("replication")
		if err != nil {
			r.runtime.Logger.Warn("exec info on %s failed %d: %+v", addr, i, err)
			continue
		}
		masterLinkStatus := iimap["master_link_status"]
		if masterLinkStatus == "up" {
			r.runtime.Logger.Info("slave link status is aleardy ok %s ~ %+v", addr, iimap)
			break
		}
		if i > maxWait {
			r.runtime.Logger.Error("wait master link up timeout ! ,please check %s :%+v", addr, iimap)
			return fmt.Errorf("LinkTimeOut:%s", addr)
		}
		time.Sleep(time.Second * time.Duration((3 + i/10)))
		r.runtime.Logger.Info("waiting link status up %s ~ %+v", addr, iimap)
	}

	if _, err := rConn.ConfigRewrite(); err != nil {
		r.runtime.Logger.Error("rewrite config %s failed :%+v", addr, err)
		return err
	}
	return nil
}

func (r *RedisLocalDoDR) backupFiles(addr string, instance ReplicaItem) error {
	bashPath := filepath.Join(r.DataDir, "redis", strconv.Itoa(instance.SlavePort))

	rdbFile, aofFile := filepath.Join(bashPath, "data", "dump.rdb"), filepath.Join(bashPath, "data", "appendonly.aof")
	bkRdb := filepath.Join("/data/dbbak", fmt.Sprintf("backup.%s.%d.%d.dump.rdb",
		r.runtime.UID, r.startTime, instance.SlavePort))
	bkAof := filepath.Join("/data/dbbak", fmt.Sprintf("backup.%s.%d.%d.appendonly.aof",
		r.runtime.UID, r.startTime, instance.SlavePort))
	if err := r.tryBackupData(aofFile, bkAof, addr); err != nil {
		return err
	}
	if err := r.tryBackupData(rdbFile, bkRdb, addr); err != nil {
		return err
	}

	redisCnf, instCnf := filepath.Join(bashPath, "redis.conf"), filepath.Join(bashPath, "instance.conf")
	if err := r.tryCommentSlaveOf(redisCnf, addr); err != nil {
		return err
	}

	if err := r.tryCommentSlaveOf(instCnf, addr); err != nil {
		return err
	}

	return nil
}

func (r *RedisLocalDoDR) tryCommentSlaveOf(cnf, addr string) error {
	if _, err := os.Stat(cnf); os.IsNotExist(err) {
		r.runtime.Logger.Info("ignore comment slaveof in file %s:%s", addr, cnf)
		return nil
	}

	// replicaof slaveof
	if rst, err := util.RunBashCmd(fmt.Sprintf("sed -i 's/slaveof /#slaveof /g; s/replicaof /#replicaof /g' %s", cnf),
		"", nil, 10*time.Second); err != nil || rst != "" {
		r.runtime.Logger.Error("backup file %s ,failed:%s:%+v", cnf, rst, err)
		return fmt.Errorf("failed by mv %s:%+v", rst, err)
	}
	return nil
}

func (r *RedisLocalDoDR) tryBackupData(src, dst, addr string) error {
	if _, err := os.Stat(src); os.IsNotExist(err) {
		r.runtime.Logger.Info("ignore backup file %s:%s:%+v", addr, src, err)
		return nil
	}
	if rst, err := util.RunBashCmd(fmt.Sprintf("mv %s %s", src, dst),
		"", nil, 10*time.Second); err != nil || rst != "" {
		r.runtime.Logger.Error("backup file %s ,failed:%s:%+v", src, rst, err)
		return fmt.Errorf("failed by mv %s:%+v", rst, err)
	}
	r.runtime.Logger.Info("backup %s [%s] 2-> [%s] succ ^_^", addr, src, dst)
	return nil
}

// tryLoginAndShutdown 登陆检查
// do bgsave [redis-cluster 理论上不会用到这个流程]
func (r *RedisLocalDoDR) tryLoginAndShutdown(addr string, password string, idx int, instance ReplicaItem) error {
	rConn, err := myredis.NewRedisClientWithTimeout(addr, password, 0, r.params.ClusterType, time.Second*10)
	if err != nil {
		r.runtime.Logger.Warn("connect instance failed %d:%s:%+v , mabye restarted machine.", idx, addr, err)
	} else {
		defer rConn.Close()
		repInfo, err := rConn.Info("replication")
		if err != nil {
			r.runtime.Logger.Warn("connect ok ,but exec info failed ?_? %d:%s:%+v", idx, addr, err)
			return fmt.Errorf("Unexpected Cmd Info result %s:%+v", addr, err)
		}
		role, master_host, master_port := repInfo["role"], repInfo["master_host"], repInfo["master_port"]
		if role != "slave" {
			r.runtime.Logger.Error("local redo dr expected [SLAVE] , but {%s} 4 %d:%s", role, idx, addr)
			return fmt.Errorf("Unexpected Role %s:%s", addr, role)
		}
		if master_host != instance.MasterIP || master_port != strconv.Itoa(instance.MasterPort) {
			r.runtime.Logger.Error("local redo dr expected [SLAVE] , but {%s} 4 %d:%s", role, idx, addr)
			return fmt.Errorf("Unexpected Role %s:%s", addr, role)
		}
		r.runtime.Logger.Info("precheck 4 instance : %s with ROLE:%s , master_host:%s,master_port:%s Succ ^_^",
			addr, role, master_host, master_port)

		if err := rConn.BgSaveAndWaitForFinish(); err != nil {
			r.runtime.Logger.Error("local redo dr bgsave failed %d:%s:%+v", idx, addr, err)
			return err
		}
		r.runtime.Logger.Info("bgsave 4 instance : :%d:%s done ^_^", idx, addr)

		if err := rConn.Shutdown(); err != nil {
			r.runtime.Logger.Error("local redo dr shutdown failed %d:%s:%+v", idx, addr, err)
			return err
		}
		r.runtime.Logger.Info("shutdown instance : :%d:%s done ^_^", idx, addr)
	}

	time.Sleep(time.Second)
	// check proces ps -ef|grep redis-server|grep $port.
	cmd01 := fmt.Sprintf(`ps -ef | grep redis-server | grep %d |grep -v grep | wc -l`, instance.SlavePort)
	pCount, err := util.RunBashCmd(cmd01, "", nil, 10*time.Second)
	if err != nil {
		r.runtime.Logger.Error("exec os cmd [%s] failed when %d:%s:%+v", cmd01, idx, addr, err)
		return err
	}

	if pCount != "0" {
		cmd01 := fmt.Sprintf(`ps -ef | grep redis-server | grep %d |grep -v grep`, instance.SlavePort)
		prst, _ := util.RunBashCmd(cmd01, "", nil, 10*time.Second)
		r.runtime.Logger.Error("redis-server process is still running %s:[%s]-{%s}", addr, pCount, prst)
		return fmt.Errorf("%s=>%s", pCount, prst)
	}

	r.runtime.Logger.Error("no [%d:%s] redis-server process running , let's continue", idx, addr)
	return nil
}

type RedisLocalDoDRParams struct {
	BkBizID      int    `json:"bk_biz_id"`
	ClusterID    int    `json:"cluster_id"`
	ClusterType  string `json:"cluster_type"`
	ImmuteDomain string `json:"immute_domain"`
	// 密码从配置文件获取
	Instances []ReplicaItem `json:"instances"`
}

// 无实际作用,仅确保实现了 jobruntime.JobRunner 接口
var _ jobruntime.JobRunner = (*RedisLocalDoDR)(nil)

// NewTendisKeysPattern  new
func NewRedisLocalDoDR() jobruntime.JobRunner {
	return &RedisLocalDoDR{}
}

// Name implements jobruntime.JobRunner.
func (r *RedisLocalDoDR) Name() string {
	return "redis_local_redo_dr"
}

// Retry implements jobruntime.JobRunner.
func (r *RedisLocalDoDR) Retry() uint {
	return 2
}

// Rollback implements jobruntime.JobRunner.
func (r *RedisLocalDoDR) Rollback() error {
	return nil
}
