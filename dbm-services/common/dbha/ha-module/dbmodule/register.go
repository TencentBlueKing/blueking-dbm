package dbmodule

import (
	"dbm-services/common/dbha/ha-module/config"
	"dbm-services/common/dbha/ha-module/constvar"
	"dbm-services/common/dbha/ha-module/dbmodule/dbmysql"
	"dbm-services/common/dbha/ha-module/dbmodule/mongodb"
	"dbm-services/common/dbha/ha-module/dbmodule/redis"
	"dbm-services/common/dbha/ha-module/dbmodule/riak"
	"dbm-services/common/dbha/ha-module/dbmodule/sqlserver"
	"dbm-services/common/dbha/ha-module/dbutil"
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
var DBCallbackMap map[string]Callback

// TODO map key try to instead of cluster type
func init() {
	DBCallbackMap = map[string]Callback{}
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

	//TwemproxyRedisInstance used
	DBCallbackMap[constvar.DetectTendisCache] = Callback{
		FetchDBCallback:              redis.TendisCacheClusterNewIns,
		DeserializeCallback:          redis.TendisCacheClusterDeserialize,
		GetSwitchInstanceInformation: redis.TendisCacheClusterNewSwitchIns,
	}

	//TwemproxyTendisSSDInstance used
	DBCallbackMap[constvar.DetectTendisSSD] = Callback{
		FetchDBCallback:              redis.TendisssdClusterNewIns,
		DeserializeCallback:          redis.TendisssdClusterDeserialize,
		GetSwitchInstanceInformation: redis.TendisssdClusterNewSwitchIns,
	}

	//PredixyTendisplusCluster used
	DBCallbackMap[constvar.DetectTendisplus] = Callback{
		FetchDBCallback:              redis.TendisplusClusterNewIns,
		DeserializeCallback:          redis.TendisplusClusterDeserialize,
		GetSwitchInstanceInformation: redis.TendisplusClusterNewSwitchIns,
	}

	//DetectRedisInstance tendis_instance used
	DBCallbackMap[constvar.DetectRedisInstance] = Callback{
		FetchDBCallback:              redis.RedisInstanceNewIns,
		DeserializeCallback:          redis.RedisInstanceDeserialize,
		GetSwitchInstanceInformation: redis.RedisInstanceNewSwitchIns,
	}

	//DetectPredixyRedisCluster used
	DBCallbackMap[constvar.DetectPredixyRedisCluster] = Callback{
		FetchDBCallback:              redis.RedisClusterNewIns,
		DeserializeCallback:          redis.RedisClusterDeserialize,
		GetSwitchInstanceInformation: redis.RedisClusterNewSwitchIns,
	}

	DBCallbackMap[constvar.Riak] = Callback{
		FetchDBCallback:              riak.NewRiakInstanceByCmDB,
		DeserializeCallback:          riak.DeserializeRiak,
		GetSwitchInstanceInformation: riak.NewRiakSwitchInstance,
	}

	//SqlserverHA used
	DBCallbackMap[constvar.SqlserverHA] = Callback{
		FetchDBCallback:              sqlserver.NewSqlserverInstanceByCmDB,
		DeserializeCallback:          sqlserver.DeserializeSqlserver,
		GetSwitchInstanceInformation: sqlserver.NewSqlserverSwitchInstance,
	}

	// Mongos used
	DBCallbackMap[constvar.MongoShardCluster] = Callback{
		FetchDBCallback:              mongodb.NewMongosInstanceByCmDB,
		DeserializeCallback:          mongodb.DeserializeMongos,
		GetSwitchInstanceInformation: mongodb.NewMongosSwitchInstance,
	}
}
