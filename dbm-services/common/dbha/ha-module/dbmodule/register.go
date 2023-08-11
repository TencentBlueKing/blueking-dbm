package dbmodule

import (
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbmodule/dbmysql"
	"dbm-services/common/dbha/ha-module/dbmodule/redis"
	"dbm-services/common/dbha/ha-module/dbmodule/riak"
	"dbm-services/common/dbha/ha-module/dbutil"
	"dbm-services/common/dbha/ha-module/types"
)

// FetchDBCallback Agent将从cmdb获取的db实例信息转换为DataBaseDetect用于探测
type FetchDBCallback func(instances []interface{}, conf *config.Config) ([]dbutil.DataBaseDetect, error)

// DeserializeCallback GM将Agent发送来的json信息转换为DataBaseDetect用于二次探测
type DeserializeCallback func(jsonInfo []byte, conf *config.Config) (dbutil.DataBaseDetect, error)

// GetSwitchInstanceInformation GQA将获取的实例信息转换为DataBaseSwitch用于切换
type GetSwitchInstanceInformation func(instance []interface{}, conf *config.Config) ([]dbutil.DataBaseSwitch, error)

// Callback TODO
type Callback struct {
	//Agent call this to fetch need detect instance list
	FetchDBCallback FetchDBCallback
	//GDM call this to get need doubleCheck instance(report by agent)
	DeserializeCallback DeserializeCallback
	//GQA call this to generate switch instance
	GetSwitchInstanceInformation GetSwitchInstanceInformation
}

// DBCallbackMap map for agent handler different dbType
var DBCallbackMap map[types.DBType]Callback

// TODO map key try to instead of cluster type
func init() {
	DBCallbackMap = map[types.DBType]Callback{}
	//TenDBHA used
	DBCallbackMap[constvar.DetectTenDBHA] = Callback{
		FetchDBCallback:              dbmysql.NewMySQLClusterByCmDB,
		DeserializeCallback:          dbmysql.DeserializeMySQL,
		GetSwitchInstanceInformation: dbmysql.NewMySQLSwitchInstance,
	}

	//TenDBCluster used
	DBCallbackMap[constvar.DetectTenDBCluster] = Callback{
		FetchDBCallback:              dbmysql.NewSpiderClusterByCmDB,
		DeserializeCallback:          dbmysql.DeserializeMySQL,
		GetSwitchInstanceInformation: dbmysql.NewMySQLSwitchInstance,
	}

	DBCallbackMap[constvar.TendisCache] = Callback{
		FetchDBCallback:              redis.NewRedisInstanceByCmdb,
		DeserializeCallback:          redis.DeserializeRedis,
		GetSwitchInstanceInformation: redis.NewRedisSwitchInstance,
	}
	DBCallbackMap[constvar.Twemproxy] = Callback{
		FetchDBCallback:              redis.NewTwemproxyInstanceByCmdb,
		DeserializeCallback:          redis.DeserializeTwemproxy,
		GetSwitchInstanceInformation: redis.NewTwemproxySwitchInstance,
	}
	DBCallbackMap[constvar.Predixy] = Callback{
		FetchDBCallback:              redis.NewPredixyInstanceByCmdb,
		DeserializeCallback:          redis.DeserializePredixy,
		GetSwitchInstanceInformation: redis.NewPredixySwitchInstance,
	}
	DBCallbackMap[constvar.Tendisplus] = Callback{
		FetchDBCallback:              redis.NewTendisplusInstanceByCmdb,
		DeserializeCallback:          redis.DeserializeTendisplus,
		GetSwitchInstanceInformation: redis.NewTendisplusSwitchInstance,
	}

	DBCallbackMap[constvar.Riak] = Callback{
		FetchDBCallback:              riak.NewRiakInstanceByCmDB,
		DeserializeCallback:          riak.DeserializeRiak,
		GetSwitchInstanceInformation: riak.NewRiakSwitchInstance,
	}
}
