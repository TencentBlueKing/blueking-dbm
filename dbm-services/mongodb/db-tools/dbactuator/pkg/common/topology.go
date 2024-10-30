package common

import (
	"fmt"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
)

// MongoNode is the node of a mongo set
type MongoNode struct {
	Role string `json:"role"`
	Ip   string `json:"ip"`
	Port int    `json:"port"`
}

// MongoSet is the set of a mongo cluster
type MongoSet struct {
	SetType string      `json:"set_type"` // shardsvr or configsvr
	SetName string      `json:"set_name"`
	Members []MongoNode `json:"members"`
}

// GetConfigShardHost get the host of the shard
func (rs *MongoSet) GetConfigShardHost() (string, error) {
	host := fmt.Sprintf("%s/", rs.SetName)
	count := 0
	for _, member := range rs.Members {
		if member.Role == "backup" { // 不会使用Backup节点导入数据.
			continue
		}
		count++
		host += fmt.Sprintf("%s:%d,", member.Ip, member.Port)
	}
	if count == 0 {
		return "", fmt.Errorf("no valid member found in shard %s", rs.SetName)
	}
	return host[:len(host)-1], nil

}

// GetConfigShardRow get the row of the shard
func (rs *MongoSet) GetConfigShardRow() (bson.D, error) {
	var shardRow = bson.D{}
	shardRow = append(shardRow, bson.E{Key: "_id", Value: rs.SetName})
	host, err := rs.GetConfigShardHost()
	if err != nil {
		return nil, err
	}
	shardRow = append(shardRow, bson.E{Key: "host", Value: host})
	shardRow = append(shardRow, bson.E{Key: "state", Value: 1})
	return shardRow, nil
}

// MongoCluster is the cluster of a mongo
type MongoCluster struct {
	ClusterType string      `json:"cluster_type"`
	Mongos      []MongoNode `json:"mongos"`
	Shards      []MongoSet  `json:"shards"`
	Configsvr   MongoSet    `json:"configsvr"`
}

// ShardIdentity is the identity of a shard
type ShardIdentity struct {
	Id                        string             `bson:"_id"`
	ClusterId                 primitive.ObjectID `bson:"clusterId"`
	ShardName                 string             `bson:"shardName"`
	ConfigsvrConnectionString string             `bson:"configsvrConnectionString"`
}
