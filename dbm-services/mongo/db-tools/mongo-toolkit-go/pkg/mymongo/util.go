package mymongo

import (
	"fmt"
	"github.com/pkg/errors"
	log "github.com/sirupsen/logrus"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"

	"go.mongodb.org/mongo-driver/mongo/options"
	"go.mongodb.org/mongo-driver/mongo/writeconcern"

	"context"
	"go.mongodb.org/mongo-driver/x/bsonx"
	"strings"
	"time"
)

const (
	AdminDB      = "admin"
	GcsBackupCol = "gcs.backup"
)

// IsMasterResult Out of IsMaster
type IsMasterResult struct {
	Hosts      []string           `json:"hosts"`
	SetName    string             `json:"setName"`
	SetVersion int                `json:"setVersion"`
	IsMaster   bool               `json:"ismaster"`
	Secondary  bool               `json:"secondary"`
	Primary    string             `json:"primary"`
	Me         string             `json:"me"`
	ElectionID primitive.ObjectID `json:"electionId"`
	LastWrite  struct {
		Optime struct {
			Ts primitive.Timestamp `json:"ts"`
			T  int                 `json:"t"`
		} `json:"opTime"`
		LastWriteDate primitive.DateTime `json:"lastWriteDate"`
	} `json:"lastWrite"`
	MaxBsonObjectSize   int                `json:"maxBsonObjectSize"`
	MaxMessageSizeBytes int                `json:"maxMessageSizeBytes"`
	MaxWriteBatchSize   int                `json:"maxWriteBatchSize"`
	LocalTime           primitive.DateTime `json:"localTime"`
	MaxWireVersion      int                `json:"maxWireVersion"`
	MinWireVersion      int                `json:"minWireVersion"`
	ReadOnly            bool               `json:"readOnly"`
	OK                  int                `json:"ok"`
}

// IsMaster Get IsMaster Result
func IsMaster(client *mongo.Client, timeoutSecond int64) (*IsMasterResult, error) {
	var result IsMasterResult
	err := RunCommand(client, "admin", "ismaster", timeoutSecond, &result)
	return &result, err
}

// GetVersion Get Version
func GetVersion(client *mongo.Client, timeoutSecond int64) (string, error) {
	type serverBuildInfo struct {
		Version      string `bson:version`
		VersionArray []int  `bson:versionArray`
	}
	var out serverBuildInfo
	err := RunCommand(client, "admin", "buildinfo", timeoutSecond, &out)
	if err != nil {
		return "", err
	}

	if len(out.VersionArray) != 4 {
		return "", errors.Errorf("bad Version:%+v", out.VersionArray)
	}
	return fmt.Sprintf("%d.%d", out.VersionArray[0], out.VersionArray[1]), nil
}

// RunCommand Get Version
func RunCommand(client *mongo.Client, db, cmd string, timeoutSecond int64, out interface{}) (err error) {
	ctx, _ := context.WithTimeout(context.Background(), time.Duration(timeoutSecond)*time.Second)
	err = client.Database(db).RunCommand(ctx, bsonx.Doc{{cmd, bsonx.Int32(1)}}).Decode(out)
	return
}

// InsertBackupHeartbeat Insert HeartBeat
func InsertBackupHeartbeat(db *mongo.Client, connObj MongoHost, backupType, dir string) (*IsMasterResult, error) {
	log.Warnf("InsertBackupHeartbeat %+v start", connObj)

	var isMasterOut IsMasterResult
	err := RunCommand(db, "admin", "isMaster", 10, &isMasterOut)
	if err != nil {
		log.Errorf("InsertBackupHeartbeat: Get isMasterResult return err: %v", err)
		return nil, err
	}
	if isMasterOut.Primary == "" {
		log.Printf("Get primary err:%v", err)
		return nil, fmt.Errorf("Get primary err:%v", err)
	}

	var masterConn *mongo.Client

	if isMasterOut.Primary != isMasterOut.Me {
		ipPort := strings.Split(isMasterOut.Primary, ":")
		connObj.Host = ipPort[0]
		connObj.Port = ipPort[1]
		masterConn, err = connObj.Connect()
		if err != nil {
			log.Errorf("InsertBackupHeartbeat: Connect to MasterHost %s:%s failed, err:%v ", connObj.Host, connObj.Port, err)
			return nil, err
		}
		defer masterConn.Disconnect(nil)
	} else {
		masterConn = db
	}

	hbObj := bson.M{}
	hbObj["_id"] = backupType
	hbObj["time"] = time.Now().Unix()
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	opts := options.Update().SetUpsert(true)
	wMajority := writeconcern.New(writeconcern.WMajority())
	collection := masterConn.Database(AdminDB).Collection(
		GcsBackupCol, &options.CollectionOptions{WriteConcern: wMajority})
	ch, err := collection.UpdateOne(ctx, bson.M{"_id": backupType}, bson.M{"$set": hbObj}, opts)
	log.Printf("InsertBackupHeartbeat %s:%d return %+v err:%s", backupType, hbObj["time"].(int64), ch, err)
	return &isMasterOut, err
}
