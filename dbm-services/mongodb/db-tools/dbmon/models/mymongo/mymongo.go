// Package mymongo TODO
package mymongo

import (
	"context"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

// MongoHost TODO
type MongoHost struct {
	Host   string
	Port   int
	User   string
	Pass   string
	AuthDb string
}

// LoginCheck TODO
func (m *MongoHost) LoginCheck(timeout int) (bool, error) {
	return true, nil
}

// ConnMongo TODO
func ConnMongo(host, port, user, pass, authdb string) (*mongo.Client, error) {
	mongoURI := fmt.Sprintf("mongodb://%s:%s@%s:%s/%s", user, pass, host, port, authdb)
	// log.Printf("conn to %s", mongoURI)
	// opts := options.Client().ApplyURI(mongoURI).SetWriteConcern(writeconcern.New(writeconcern.WMajority()))
	opts := options.Client().ApplyURI(mongoURI)
	client, err := mongo.NewClient(opts)
	if err != nil {
		return nil, err
	}
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()
	err = client.Connect(ctx)
	if err != nil {
		return nil, err
	}
	// defer client.Disconnect(ctx)
	return client, err

}
