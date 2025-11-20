package logical

import (
	"context"
	"dbm-services/mongodb/db-tools/mongo-toolkit-go/pkg/mymongo"
	"time"

	"github.com/pkg/errors"
	"go.mongodb.org/mongo-driver/bson"
)

// DbCollection dbName和collectionList和不匹配的collectionList的结构体
type DbCollection struct {
	Db         string
	Col        []string
	notMachCol []string
}

var ErrorNoMatchDb error = errors.New("NoMatchDb")

// GetDbCollectionWithFilter 获取指定mongo的所有db和collection
func GetDbCollectionWithFilter(ip, port, user, pass, authDb string, filter *NsFilter, excludeSysDb bool) (
	[]DbCollection, error) {
	client, err := mymongo.Connect(ip, port, user, pass, authDb, 60*time.Second)
	if err != nil {
		return nil, errors.Wrap(err, "Connect")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	dbList, err := client.ListDatabaseNames(ctx, bson.M{})
	if err != nil {
		cancel()
		return nil, errors.Wrap(err, "ListDatabaseNames")
	}
	cancel()

	var dbColList []DbCollection
	for _, dbName := range dbList {
		if excludeSysDb && mymongo.IsSysDb(dbName) {
			continue
		}
		ctx, cancel := context.WithTimeout(context.Background(), 300*time.Second)
		colList, err := client.Database(dbName).ListCollectionNames(ctx, bson.M{})
		if err != nil {
			cancel()
			return nil, errors.Wrap(err, "ListCollectionNames")
		}
		cancel()
		matched, notMatched := filter.FilterTbV2(dbName, colList)
		dbColList = append(dbColList, DbCollection{
			Db:         dbName,
			Col:        matched,
			notMachCol: notMatched,
		})
	}
	return dbColList, nil
}

// GetDbCollection 获取指定mongo的所有db和collection.
// 如果excludeSysDb为true, 则不包括系统库.
func GetDbCollection(ip, port, user, pass, authDb string, excludeSysDb bool) ([]DbCollection, error) {
	client, err := mymongo.Connect(ip, port, user, pass, authDb, 60*time.Second)
	if err != nil {
		return nil, errors.Wrap(err, "Connect")
	}
	defer client.Disconnect(context.Background())
	ctx, cancel := context.WithTimeout(context.Background(), 60*time.Second)
	dbList, err := client.ListDatabaseNames(ctx, bson.M{})
	defer cancel()

	if err != nil {
		return nil, errors.Wrap(err, "ListDatabaseNames")
	}
	var dbColList []DbCollection
	for _, dbName := range dbList {
		if excludeSysDb && mymongo.IsSysDb(dbName) {
			continue
		}
		if colList, err := client.Database(dbName).ListCollectionNames(ctx, bson.M{}); err == nil {
			dbColList = append(dbColList, DbCollection{
				Db:  dbName,
				Col: colList,
			})
		} else {
			return nil, errors.Wrap(err, "ListCollectionNames")
		}
	}
	return dbColList, nil
}
