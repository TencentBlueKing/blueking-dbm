package logical

import (
	"context"
	"dbm-services/mongo/db-tools/mongo-toolkit-go/pkg/mymongo"
	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
	"time"
)

// DbCollection dbName和collectionList和不匹配的collectionList的结构体
type DbCollection struct {
	Db         string
	Col        []string
	notMachCol []string
}

// GetDbCollectionWithFilter 获取指定mongo的所有db和collection
func GetDbCollectionWithFilter(ip, port, user, pass, authDb string, filter *NsFilter) ([]DbCollection, error) {
	client, err := mymongo.Connect(ip, port, user, pass, authDb, 60*time.Second)
	if err != nil {
		return nil, errors.Wrap(err, "Connect")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	dbList, err := client.ListDatabaseNames(ctx, bson.M{})
	if err != nil {
		return nil, errors.Wrap(err, "ListDatabaseNames")
	}
	cancel()

	matchDbList, _ := filter.FilterDb(dbList)
	// 如果按照输入的db过滤后，没有db了，就报错
	if len(matchDbList) == 0 {
		return nil, errors.New("no match db")
	}

	var dbColList []DbCollection

	for _, dbName := range matchDbList {
		ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
		colList, err := client.Database(dbName).ListCollectionNames(ctx, bson.M{})
		if err != nil {
			return nil, errors.Wrap(err, "ListCollectionNames")
		}
		cancel()

		var dbCol DbCollection
		dbCol.Db = dbName
		dbCol.Col, dbCol.notMachCol = filter.FilterTb(colList)
		dbColList = append(dbColList, dbCol)
	}
	return dbColList, nil
}

// GetDbCollection 获取指定mongo的所有db和collection
func GetDbCollection(ip, port, user, pass, authDb string, excludeSysDb bool) ([]DbCollection, error) {
	client, err := mymongo.Connect(ip, port, user, pass, authDb, 60*time.Second)
	if err != nil {
		return nil, errors.Wrap(err, "Connect")
	}
	defer client.Disconnect(context.Background())
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	dbList, err := client.ListDatabaseNames(ctx, bson.M{})
	if err != nil {
		return nil, errors.Wrap(err, "ListDatabaseNames")
	}
	cancel()
	var dbColList []DbCollection
	for _, dbName := range dbList {
		if excludeSysDb && mymongo.IsSysDb(dbName) {
			continue
		}
		ctx, cancel := context.WithTimeout(context.Background(), 120*time.Second)
		colList, err := client.Database(dbName).ListCollectionNames(ctx, bson.M{})
		if err != nil {
			return nil, errors.Wrap(err, "ListCollectionNames")
		}
		cancel()

		var dbCol DbCollection
		dbCol.Db = dbName
		dbCol.Col = colList
		dbCol.notMachCol = nil
		dbColList = append(dbColList, dbCol)
	}
	return dbColList, nil
}
